import asyncio
import json
import logging
import math
import os
import sys
import tempfile
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import httpx

from app.config import settings
from app.integrations.forex import forex_service
from app.rag import rag_service
from app.schemas.trip import (
    Accommodation,
    Activity,
    BudgetBreakdown,
    DayPlan,
    TripResult,
)
from app.tools.stay_activity_tools import recommend_stays_and_activities
from app.tools.transport_tools import estimate_transport

from . import mcp_tools
from .models import Event, Evidence, Status, TripState, clean
from .specialists import Narrative


def research_client():
    return httpx.AsyncClient(timeout=60)


async def request_research(state):
    message = {
        "role": "user",
        "kind": "message",
        "messageId": state.trip_id,
        "contextId": state.trip_id,
        "parts": [{"kind": "data", "data": state.preferences.model_dump(mode="json")}],
    }
    async with research_client() as client:
        response = await client.post(
            settings.research_base_url + "/a2a",
            headers={"Authorization": "Bearer " + settings.adk_service_token},
            json={
                "id": state.trip_id,
                "jsonrpc": "2.0",
                "method": "message/send",
                "params": {"message": message},
            },
        )
        response.raise_for_status()
        reply = response.json()
    if (
        reply.get("id") != state.trip_id
        or reply.get("jsonrpc") != "2.0"
        or "error" in reply
    ):
        raise RuntimeError("Research service failed")
    task = reply["result"]
    if task["contextId"] != state.trip_id or task["status"]["state"] != "completed":
        raise RuntimeError("Research correlation failed")
    return task["artifacts"][0]["parts"][0]["data"]


async def execute_crew(context):
    with tempfile.TemporaryDirectory(prefix="trippy-") as tmp:
        output = Path(tmp) / "result.json"
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "app.planning.crew_worker",
            str(output),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
            env={
                **os.environ,
                "HOME": tmp,
                "XDG_CACHE_HOME": tmp,
                "CREWAI_STORAGE_DIR": tmp,
                "CREWAI_DISABLE_TELEMETRY": "true",
                "CREWAI_TRACING_ENABLED": "false",
                "LITELLM_LOCAL_MODEL_COST_MAP": "True",
                "OTEL_SDK_DISABLED": "true",
            },
        )
        try:
            async with asyncio.timeout(155):
                await proc.communicate(json.dumps(context).encode())
            if proc.returncode != 0:
                failure = json.loads(output.read_text(encoding="utf-8")) if output.exists() else {}
                logging.getLogger("trippy").warning("Itinerary worker exit=%s error=%s status=%s frames=%s", proc.returncode, failure.get("error"), failure.get("status"), failure.get("frames"))
                raise RuntimeError("CrewAI planning unavailable")
            data = json.loads(output.read_text(encoding="utf-8"))
            return Narrative.model_validate(data["plan"]), [
                Event.model_validate(e) for e in data["events"]
            ]
        finally:
            if proc.returncode is None:
                proc.kill()
                await proc.wait()


def evidence(state, label, source, status, detail=""):
    confidence = {
        Status.LIVE: "moderate",
        Status.VERIFIED: "high",
        Status.ESTIMATED: "low",
        Status.UNKNOWN: "unknown",
    }[status]
    state.evidence.append(
        Evidence(
            label=label,
            source=source,
            status=status,
            confidence=confidence,
            detail=detail,
        )
    )


def check_budget(budget, components):
    cents = Decimal("0.01")
    base = sum(Decimal(str(v)).quantize(cents) for v in components)
    contingency = (base * Decimal("0.08")).quantize(cents)
    actual = [
        budget.transport,
        budget.accommodation,
        budget.activities,
        budget.food_estimate,
    ]
    if (
        actual != list(components)
        or Decimal(str(budget.miscellaneous)) != contingency
        or Decimal(str(budget.total)) != base + contingency
    ):
        raise ValueError("Budget reconciliation failed")


async def build_plan(p):
    state = TripState(preferences=p)
    data = await request_research(state)
    state.destination = clean(data["destination"], 200)
    if not state.destination or (
        p.destinations and state.destination != p.destinations[0]
    ):
        raise ValueError("Research returned a different destination")
    state.events.extend(Event.model_validate(e) for e in data["events"])
    city = state.destination
    days = (p.end_date - p.start_date).days
    code = p.currency.upper()
    rates = await forex_service.get_rates("USD") if code != "USD" else {"USD": 1.0}
    rate = rates.get(code)
    if not rate or not math.isfinite(rate) or rate <= 0:
        raise ValueError("Unsupported currency")
    evidence(
        state,
        "Planning exchange rate",
        "USD base or exchange-rate service with offline reference rates",
        Status.ESTIMATED,
        f"1 USD = {rate:g} {code}",
    )
    async with mcp_tools.connect() as session:

        async def tool(name, **args):
            return await mcp_tools.call(session, state, name, **args)

        info = await tool("search_destination_info", destination=city)
        registry = await tool("lookup_travel_records", destination=city)
        weather = await tool(
            "get_weather",
            destination=city,
            start=str(p.start_date),
            end=str(p.end_date),
        )
        route = await tool(
            "get_route",
            origin=p.origin,
            destination=city,
            mode=p.preferred_transport.value,
        )
        evidence(
            state,
            "Geocoding",
            data.get("geocoder", "Open-Meteo geocoding"),
            Status.LIVE,
            f"{city} - {data['latitude']:.3f}, {data['longitude']:.3f}",
        )
        evidence(
            state,
            "Destination information",
            "Wikipedia",
            Status.LIVE
            if info.get("summary") or info.get("places")
            else Status.UNKNOWN,
        )
        for label, record in (("Weather", weather), ("Route", route)):
            evidence(
                state,
                label,
                record.get("provider_name", "No available source"),
                Status.LIVE
                if record.get("is_live")
                else Status.ESTIMATED
                if record
                else Status.UNKNOWN,
            )
        for item in registry["facts"]:
            evidence(
                state,
                item["title"],
                item["source"],
                Status.VERIFIED,
                item["fact"] + " Source checked " + item["checked_on"] + ".",
            )
        for guide in registry["records"]:
            evidence(
                state, "Bundled guide", guide["file"], Status.VERIFIED, guide["title"]
            )
        evidence(
            state,
            "Bookable prices and availability",
            "No inventory provider",
            Status.UNKNOWN,
        )
        evidence(
            state,
            "Group budget",
            "TRIPPY planning allowances",
            Status.ESTIMATED,
            "Two travelers per room, rounded up. Group allowances include all nights, meals, activities, return transport and 8% contingency.",
        )
        for level in range(3):
            state.refinements = level
            transport = estimate_transport(
                p.origin,
                city,
                p.preferred_transport,
                travelers=p.travelers,
                travel_style=p.travel_style,
                refinement_level=level,
                currency=code,
                live_forex_rate=rate,
            )
            stay = recommend_stays_and_activities(
                city,
                p.travel_style,
                p.start_date,
                days,
                travelers=p.travelers,
                refinement_level=level,
                currency=code,
                live_forex_rate=rate,
            )
            amounts = (
                transport.total_cost,
                stay.total_accommodation_cost,
                stay.total_activities_cost,
                stay.total_food_cost,
            )
            totals = await tool(
                "calculate_trip_budget",
                transport=amounts[0],
                lodging=amounts[1],
                activities=amounts[2],
                food=amounts[3],
                currency=code,
            )
            budget = BudgetBreakdown.model_validate(totals)
            check_budget(budget, amounts)
            if p.budget_max is None or budget.total <= p.budget_max:
                break
    passages = rag_service.retrieve(
        city + " " + " ".join(p.interests), destination=city, top_k=3
    )
    context = {
        "destination": city,
        "days": days,
        "preferences": p.model_dump(mode="json"),
        "research": clean(data.get("summary", "")),
        "places": [clean(x["name"], 100) for x in info.get("places", [])],
        "guide_excerpt": [clean(x.text, 500) for x in passages],
        "budget_estimate": budget.model_dump(),
        "refinements": state.refinements,
        "evidence": [e.model_dump(mode="json") for e in state.evidence],
        "route": route,
        "weather": weather,
    }
    plan, events = await execute_crew(context)
    state.events.extend(events)
    check_budget(budget, amounts)
    if len(plan.days) != days:
        raise ValueError("Incomplete daily plan")
    itinerary = []
    for index, row in enumerate(plan.days):
        date = p.start_date + timedelta(days=index)
        legs = []
        if index == 0:
            legs.append(transport.legs[0])
        if index == days - 1:
            legs.append(transport.legs[-1])
        itinerary.append(
            DayPlan(
                day=index + 1,
                date=date,
                activities=[
                    Activity(
                        name=clean(row.activity),
                        description=clean(row.description),
                        location=city,
                        date=date,
                    )
                ],
                accommodation=Accommodation(
                    name=clean(plan.lodging_category),
                    location=city,
                    check_in=date,
                    check_out=date + timedelta(days=1),
                    cost_per_night=stay.cost_per_night,
                ),
                transport=legs,
            )
        )
    warnings = [
        "Group costs are planning estimates. Check prices, schedules and availability before booking."
    ]
    if p.budget_max is not None and budget.total > p.budget_max:
        warnings.append(
            f"Budget advisory: the group estimate exceeds your limit by {code} {budget.total - p.budget_max:.2f} after two refinements."
        )
    return TripResult(
        trip_id=state.trip_id,
        preferences=p,
        destinations=[city],
        currency=code,
        budget=budget,
        itinerary=itinerary,
        summary=clean(plan.summary, 1200),
        warnings=warnings,
        weather=weather or None,
        route_estimate=route or None,
        rag_sources=[x["title"] for x in registry["records"]],
        destination_guidance=[clean(x.text, 500) for x in passages],
        evidence=[e.model_dump(mode="json") for e in state.evidence],
        execution=[e.model_dump() for e in state.events],
    ), state
