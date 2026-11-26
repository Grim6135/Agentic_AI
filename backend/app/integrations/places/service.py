"""
TRIPPY Backend — Real-World Places & Landmarks Integration Service

Discovers authentic points of interest, cultural landmarks, monuments,
and destination summaries using Wikipedia Geosearch & REST APIs.
Provides real-world attractions and context for any geocoded location worldwide.
"""

from urllib.parse import quote
from dataclasses import dataclass, field
import logging
import time
from typing import Dict, List, Optional, Tuple
import httpx

logger = logging.getLogger("trippy.places")


@dataclass
class PlacePOI:
    name: str
    description: str = ""
    distance_meters: float = 0.0
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    source_url: Optional[str] = None


@dataclass
class DestinationInfo:
    title: str
    summary: str
    coordinates: Optional[Tuple[float, float]] = None
    landmarks: List[PlacePOI] = field(default_factory=list)


class PlacesService:
    """Fetches real-world landmarks and tourist highlights using Wikipedia Geosearch."""

    def __init__(self, timeout: float = 5.0, cache_ttl: int = 86400):
        self.timeout = timeout
        self.cache_ttl = cache_ttl
        self._headers = {
            "User-Agent": "TrippyTravelPlanner/1.0 (https://github.com/trippy/trippy; info@trippy.local)"
        }
        self._cache: Dict[tuple, Tuple[float, DestinationInfo]] = {}

    async def get_destination_info(
        self,
        city_name: str,
        coordinates: Optional[Tuple[float, float]] = None,
    ) -> Optional[DestinationInfo]:
        """
        Retrieves real-world summary and nearby landmarks for a destination.
        """
        clean_name = city_name.split(",")[0].strip()
        cache_key = (city_name.casefold(), coordinates)

        now = time.time()
        if cache_key in self._cache:
            ts, info = self._cache[cache_key]
            if now - ts < self.cache_ttl:
                return info

        summary_text = ""
        resolved_coords = coordinates

        # 1. Fetch Wikipedia Page Summary for the city/destination
        try:
            url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(clean_name.replace(' ', '_'), safe='')}"
            async with httpx.AsyncClient(timeout=self.timeout, headers=self._headers, follow_redirects=True) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    summary_text = data.get("extract", "")
                    if not resolved_coords and "coordinates" in data:
                        resolved_coords = (
                            float(data["coordinates"]["lat"]),
                            float(data["coordinates"]["lon"]),
                        )
        except Exception as e:
            logger.debug(f"Wiki summary failed for {clean_name}: {e}")

        # 2. Fetch Nearby Points of Interest via Wikipedia Geosearch & Landmark Search
        landmarks: List[PlacePOI] = []
        ignored_patterns = (
            "siege of", "battle of", "timeline of", "history of", "list of", "lists of",
            "outline of", "treaty of", "commune", "census", "election", "airport", "railway station",
            "tourist attraction", "landmarks in"
        )

        def is_valid_poi(t: str) -> bool:
            tl = t.lower()
            if tl == clean_name.lower():
                return False
            return not any(pat in tl for pat in ignored_patterns)

        if resolved_coords:
            lat, lon = resolved_coords
            try:
                geo_url = "https://en.wikipedia.org/w/api.php"
                params = {
                    "action": "query",
                    "list": "geosearch",
                    "gscoord": f"{lat}|{lon}",
                    "gsradius": 10000,  # 10km radius (Wikipedia API maximum)
                    "gslimit": 15,
                    "format": "json",
                }
                async with httpx.AsyncClient(timeout=self.timeout, headers=self._headers, follow_redirects=True) as client:
                    geo_res = await client.get(geo_url, params=params)
                    if geo_res.status_code == 200:
                        results = geo_res.json().get("query", {}).get("geosearch", [])
                        for item in results:
                            title = item.get("title", "")
                            if is_valid_poi(title):
                                landmarks.append(
                                    PlacePOI(
                                        name=title,
                                        distance_meters=float(item.get("dist", 0.0)),
                                        latitude=float(item.get("lat", 0.0)),
                                        longitude=float(item.get("lon", 0.0)),
                                        source_url=f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                                    )
                                )
            except Exception as e:
                logger.debug(f"Wiki geosearch failed for {clean_name}: {e}")

        # If geosearch returned few landmarks, supplement with verified Wikipedia landmark search
        if len(landmarks) < 4:
            try:
                search_url = "https://en.wikipedia.org/w/api.php"
                sparams = {
                    "action": "query",
                    "list": "search",
                    "srsearch": f"{clean_name} landmarks attractions monuments",
                    "srlimit": 10,
                    "format": "json",
                }
                async with httpx.AsyncClient(timeout=self.timeout, headers=self._headers, follow_redirects=True) as client:
                    s_res = await client.get(search_url, params=sparams)
                    if s_res.status_code == 200:
                        s_results = s_res.json().get("query", {}).get("search", [])
                        existing_names = {lm.name.lower() for lm in landmarks}
                        for item in s_results:
                            title = item.get("title", "")
                            if is_valid_poi(title) and title.lower() not in existing_names:
                                landmarks.append(
                                    PlacePOI(
                                        name=title,
                                        description=item.get("snippet", ""),
                                        source_url=f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                                    )
                                )
                                existing_names.add(title.lower())
            except Exception as e:
                logger.debug(f"Wiki landmark search failed for {clean_name}: {e}")

        info = DestinationInfo(
            title=clean_name,
            summary=summary_text,
            coordinates=resolved_coords,
            landmarks=landmarks,
        )
        self._cache[cache_key] = (now, info)
        return info


places_service = PlacesService()
