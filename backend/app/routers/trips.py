import asyncio
import logging
from time import monotonic

from fastapi import APIRouter, Header, HTTPException, Request, Response

from app.config import settings
from app.planning import store
from app.planning.geocode import UnknownLocation, resolve
from app.planning.models import safe_inputs
from app.schemas.trip import TripPreferences, TripResult

router = APIRouter(prefix="/trips", tags=["trips"])


@router.post("/plan", response_model=TripResult)
async def plan_trip(preferences: TripPreferences, request: Request, response: Response):
    from app.planning.workflow import build_plan

    if not safe_inputs(preferences):
        raise HTTPException(
            422, "Please enter travel preferences without embedded instructions."
        )
    if not settings.model_key(settings.crew_model) or not settings.adk_service_token:
        raise HTTPException(503, "The travel planning providers are not configured.")
    try:
        admitted = store.admit(request.client.host if request.client else "unknown")
    except Exception as exc:
        logging.getLogger("trippy").warning("Quota storage unavailable (%s)", type(exc).__name__)
        raise HTTPException(503, "Trip storage is temporarily unavailable.") from None
    if not admitted:
        raise HTTPException(429, "Planning limit reached. Try again in the next hour.")
    started = monotonic()
    try:
        async with asyncio.timeout(250):
            await resolve(preferences.origin)
            if preferences.destinations:
                await resolve(preferences.destinations[0])
            result, state = await build_plan(preferences)
        result.access_token = store.save(result, state)
        from app.planning.tracing import export

        export(state, monotonic() - started)
    except UnknownLocation:
        raise HTTPException(
            422, "The origin or destination could not be verified."
        ) from None
    except Exception as exc:
        logging.getLogger("trippy").warning(
            "Trip planning failed (%s)", type(exc).__name__
        )
        raise HTTPException(
            503, "Trip planning is temporarily unavailable. Please try again."
        ) from None
    response.headers["Cache-Control"] = "private, no-store"
    return result


def owned(trip_id, authorization, trace):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "A trip access token is required")
    value = store.read(trip_id, authorization[7:], trace)
    if value is None:
        raise HTTPException(404, "Trip unavailable")
    return Response(
        value,
        media_type="application/json",
        headers={"Cache-Control": "private, no-store"},
    )


@router.get("/{trip_id}/trace")
def get_trace(trip_id: str, authorization: str = Header(default="")):
    return owned(trip_id, authorization, True)


@router.get("/{trip_id}", response_model=TripResult)
def get_trip(trip_id: str, authorization: str = Header(default="")):
    return owned(trip_id, authorization, False)


@router.get("")
def list_trips():
    raise HTTPException(403, "Use the private link for your trip")
