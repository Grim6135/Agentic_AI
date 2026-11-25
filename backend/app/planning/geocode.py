"""Resolve user-entered city/country pairs without treating an outage as a bad location."""

import httpx


class UnknownLocation(ValueError):
    pass


async def resolve(city: str) -> tuple[float, float]:
    name, _, region = city.partition(",")
    region = region.strip().casefold()
    region = {"usa": "us", "uk": "gb"}.get(region, region)
    async with httpx.AsyncClient(
        timeout=10, transport=httpx.AsyncHTTPTransport(retries=1)
    ) as client:
        result = await client.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={
                "name": name.strip(),
                "count": 10,
                "language": "en",
                "format": "json",
            },
        )
        result.raise_for_status()
    for candidate in result.json().get("results", []):
        values = {
            str(candidate.get(k, "")).casefold()
            for k in ("country", "country_code", "admin1")
        }
        if not region or region in values:
            return float(candidate["latitude"]), float(candidate["longitude"])
    raise UnknownLocation("Location could not be verified")
