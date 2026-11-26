"""Expose only the MCP arguments already approved for this trip and specialist."""

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from types import SimpleNamespace


def for_specialist(role: str, context: dict, events: list):
    from crewai.tools import tool

    from . import mcp_tools

    p = context["preferences"]
    destination = context["destination"]
    budget = context["budget_estimate"]
    permitted = {
        "Destination Specialist": [
            ("search_destination_info", {"destination": destination})
        ],
        "Transport Specialist": [
            (
                "get_route",
                {
                    "origin": p["origin"],
                    "destination": destination,
                    "mode": p["preferred_transport"],
                },
            )
        ],
        "Stay & Activity Specialist": [
            ("lookup_travel_records", {"destination": destination}),
            (
                "get_weather",
                {
                    "destination": destination,
                    "start": p["start_date"],
                    "end": p["end_date"],
                },
            ),
        ],
        "Budget Specialist": [
            (
                "calculate_trip_budget",
                {
                    "transport": budget["transport"],
                    "lodging": budget["accommodation"],
                    "activities": budget["activities"],
                    "food": budget["food_estimate"],
                    "currency": budget["currency"],
                },
            )
        ],
        "Itinerary Specialist": [],
    }

    def bind(name, args):
        lock = Lock()
        cached = []

        @tool(name)
        def lookup() -> str:
            """Check the approved trip evidence for this task. Takes no arguments."""

            async def request():
                async with mcp_tools.connect() as session:
                    return await mcp_tools.call(
                        session, SimpleNamespace(events=events), name, **args
                    )

            with lock:
                if not cached:
                    with ThreadPoolExecutor(max_workers=1) as pool:
                        result = pool.submit(lambda: asyncio.run(request())).result()
                    cached.append(json.dumps(result, ensure_ascii=False))
                return cached[0]

        return lookup

    return [bind(name, args) for name, args in permitted[role]]
