"""Geocode cities using Open-Meteo, or Photon when the primary service is unavailable."""
import httpx


class UnknownLocation(ValueError):
    pass


async def locate(city: str) -> tuple[tuple[float, float], str]:
    name, _, region = city.partition(",")
    name = name.strip()
    region = region.strip().casefold()
    region = {"usa": "us", "uk": "gb"}.get(region, region)
    async with httpx.AsyncClient(timeout=7) as client:
        try:
            response = await client.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": name, "count": 10, "language": "en", "format": "json"},
            )
            response.raise_for_status()
        except httpx.HTTPError:
            response = await client.get(
                "https://photon.komoot.io/api/",
                params={"q": city, "limit": 5, "lang": "en"},
            )
            response.raise_for_status()
            for feature in response.json().get("features", []):
                place = feature["properties"]
                regions = {str(place.get(k, "")).casefold() for k in ("country", "countrycode", "state")}
                if place.get("name", "").casefold() == name.casefold() and (not region or region in regions):
                    lon, lat = feature["geometry"]["coordinates"]
                    return (float(lat), float(lon)), "Photon / OpenStreetMap"
        else:
            for candidate in response.json().get("results", []):
                regions = {str(candidate.get(k, "")).casefold() for k in ("country", "country_code", "admin1")}
                if not region or region in regions:
                    return (float(candidate["latitude"]), float(candidate["longitude"])), "Open-Meteo geocoding"
    raise UnknownLocation("Location could not be verified")


async def resolve(city: str) -> tuple[float, float]:
    coordinates, _ = await locate(city)
    return coordinates
