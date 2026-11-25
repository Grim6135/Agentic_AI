import re
from datetime import UTC, datetime
from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from app.schemas.trip import TripPreferences


class Status(str, Enum):
    LIVE = "LIVE"
    VERIFIED = "VERIFIED"
    ESTIMATED = "ESTIMATED"
    UNKNOWN = "UNKNOWN"


class Evidence(BaseModel):
    label: str
    source: str
    status: Status
    confidence: Literal["high", "moderate", "low", "unknown"]
    observed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    detail: str = ""


class Event(BaseModel):
    component: str
    action: str
    elapsed_ms: int = Field(ge=0)
    tokens: int | None = Field(default=None, ge=0)


class TripState(BaseModel):
    trip_id: str = Field(default_factory=lambda: "trip_" + uuid4().hex)
    preferences: TripPreferences
    destination: str = ""
    refinements: int = Field(default=0, ge=0, le=2)
    evidence: list[Evidence] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)


INSTRUCTION = re.compile(
    r"ignore\s+(?:all\s+)?(?:previous|prior|above|system)\s+instructions|(?:reveal|print|show)\s+(?:the\s+)?(?:system prompt|api keys?)|<\|(?:system|assistant)|\[/?INST\]",
    re.I,
)


def clean(value: str, limit: int = 800) -> str:
    return INSTRUCTION.sub("[removed]", " ".join(value.split()))[:limit]


def safe_inputs(p: TripPreferences) -> bool:
    return not any(
        INSTRUCTION.search(s)
        for s in [p.origin, *(p.destinations or []), *p.interests, p.notes or ""]
    )
