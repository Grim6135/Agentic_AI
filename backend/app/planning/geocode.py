"""Geocode cities using Open-Meteo, or Photon when the primary service is unavailable."""
import httpx


class UnknownLocation(ValueError):
    pass


HEADERS = {"User-Agent": "TRIPPY/0.4.0 (travel-planner; contact@trippy.local)"}


async def locate(city: str) -> tuple[tuple[float, float], str]:
    name, _, region = city.partition(",")
    name = name.strip()
    region = region.strip().casefold()
    region = {"usa": "us", "uk": "gb"}.get(region, region)
    async with httpx.AsyncClient(timeout=7, headers=HEADERS) as client:
        try:
            response = await client.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": name, "count": 10, "language": "en", "format": "json"},
            )
            response.raise_for_status()
            for candidate in response.json().get("results", []):
                regions = {str(candidate.get(k, "")).casefold() for k in ("country", "country_code", "admin1")}
                if not region or region in regions:
                    return (float(candidate["latitude"]), float(candidate["longitude"])), "Open-Meteo geocoding"
        except Exception:
            pass

        try:
            response = await client.get(
                "https://photon.komoot.io/api/",
                params={"q": city, "limit": 5, "lang": "en"},
            )
            response.raise_for_status()
            for feature in response.json().get("features", []):
                place = feature.get("properties", {})
                regions = {str(place.get(k, "")).casefold() for k in ("country", "countrycode", "state")}
                if place.get("name", "").casefold() == name.casefold() and (not region or region in regions):
                    lon, lat = feature["geometry"]["coordinates"]
                    return (float(lat), float(lon)), "Photon / OpenStreetMap"
            features = response.json().get("features", [])
            if features:
                lon, lat = features[0]["geometry"]["coordinates"]
                return (float(lat), float(lon)), "Photon / OpenStreetMap"
        except Exception:
            pass

        try:
            response = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": city, "format": "json", "limit": 1},
            )
            response.raise_for_status()
            items = response.json()
            if items:
                return (float(items[0]["lat"]), float(items[0]["lon"])), "Nominatim / OpenStreetMap"
        except Exception:
            pass
    raise UnknownLocation("Location could not be verified")


async def resolve(city: str) -> tuple[float, float]:
    coordinates, _ = await locate(city)
    return coordinates
