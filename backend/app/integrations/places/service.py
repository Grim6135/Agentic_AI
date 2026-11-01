"""
TRIPPY Backend — Real-World Places & Landmarks Integration Service

Discovers authentic points of interest, cultural landmarks, monuments,
and destination summaries using Wikipedia Geosearch & REST APIs.
Provides real-world attractions and context for any geocoded location worldwide.
"""

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
        self._cache: Dict[str, Tuple[float, DestinationInfo]] = {}

    async def get_destination_info(
        self,
        city_name: str,
        coordinates: Optional[Tuple[float, float]] = None,
    ) -> Optional[DestinationInfo]:
        """
        Retrieves real-world summary and nearby landmarks for a destination.
        """
        clean_name = city_name.split(",")[0].strip()
        cache_key = clean_name.lower()

        now = time.time()
        if cache_key in self._cache:
            ts, info = self._cache[cache_key]
            if now - ts < self.cache_ttl:
                return info

        summary_text = ""
        resolved_coords = coordinates

        # 1. Fetch Wikipedia Page Summary for the city/destination
        try:
            url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{clean_name.replace(' ', '_')}"
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

        # 2. Fetch Nearby Points of Interest via Wikipedia Geosearch
        landmarks: List[PlacePOI] = []
        if resolved_coords:
            lat, lon = resolved_coords
            try:
                geo_url = "https://en.wikipedia.org/w/api.php"
                params = {
                    "action": "query",
                    "list": "geosearch",
                    "gscoord": f"{lat}|{lon}",
                    "gsradius": 15000,  # 15km radius
                    "gslimit": 12,
                    "format": "json",
                }
                async with httpx.AsyncClient(timeout=self.timeout, headers=self._headers, follow_redirects=True) as client:
                    geo_res = await client.get(geo_url, params=params)
                    if geo_res.status_code == 200:
                        results = geo_res.json().get("query", {}).get("geosearch", [])
                        for item in results:
                            title = item.get("title", "")
                            # Filter out self-title or general district name if exact match
                            if title.lower() != clean_name.lower():
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

        info = DestinationInfo(
            title=clean_name,
            summary=summary_text,
            coordinates=resolved_coords,
            landmarks=landmarks,
        )
        self._cache[cache_key] = (now, info)
        return info


places_service = PlacesService()
