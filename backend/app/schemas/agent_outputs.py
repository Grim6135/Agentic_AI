"""
TRIPPY Backend — Agent Output Schemas

Typed Pydantic models for the outputs produced by each of the
five CrewAI agents: Destination, Transport, Stay & Activity,
Budget, and Itinerary.
"""

from typing import List, Optional
from pydantic import BaseModel, Field

from app.schemas.trip import (
    Activity,
    BudgetBreakdown,
    DayPlan,
    TransportLeg,
    TransportMode,
    TravelStyle,
)


# ─── 1. Destination Agent Outputs ────────────────────────────────────────

class DestinationCandidate(BaseModel):
    name: str = Field(..., examples=["Kyoto, Japan"])
    country: str = Field(..., examples=["Japan"])
    rank: int = Field(..., ge=1)
    match_score: float = Field(..., ge=0.0, le=100.0, description="Match score out of 100")
    highlights: List[str] = Field(default_factory=list)
    recommended_days: int = Field(..., ge=1)
    why_matched: str


class DestinationAgentOutput(BaseModel):
    selected_destination: str
    candidates: List[DestinationCandidate] = Field(default_factory=list)
    rationale: str


# ─── 2. Transport Agent Outputs ──────────────────────────────────────────

class TransportAgentOutput(BaseModel):
    legs: List[TransportLeg] = Field(default_factory=list)
    total_cost: float = Field(default=0.0, ge=0.0)
    total_duration_hours: float = Field(default=0.0, ge=0.0)
    primary_mode: TransportMode = TransportMode.mixed
    alternatives: List[str] = Field(default_factory=list)


# ─── 3. Stay & Activity Agent Outputs ────────────────────────────────────

class StayActivityAgentOutput(BaseModel):
    accommodation_name: str
    accommodation_category: str = Field(
        default="midscale",
        description="Tier: budget, midscale, boutique, or luxury",
    )
    cost_per_night: float = Field(default=0.0, ge=0.0)
    total_accommodation_cost: float = Field(default=0.0, ge=0.0)
    activities: List[Activity] = Field(default_factory=list)
    total_activities_cost: float = Field(default=0.0, ge=0.0)
    daily_food_cost: float = Field(default=0.0, ge=0.0)
    total_food_cost: float = Field(default=0.0, ge=0.0)
    food_highlights: List[str] = Field(default_factory=list)


# ─── 4. Budget Agent Outputs ─────────────────────────────────────────────

class BudgetReductionProposal(BaseModel):
    category: str = Field(..., description="accommodation, transport, activities, or food")
    action: str = Field(..., description="Specific recommended adjustment")
    estimated_savings: float = Field(..., ge=0.0)
    description: str


class BudgetAgentOutput(BaseModel):
    breakdown: BudgetBreakdown
    budget_max: Optional[float] = None
    is_within_budget: bool = True
    overflow_amount: float = Field(default=0.0, ge=0.0)
    reduction_proposals: List[BudgetReductionProposal] = Field(default_factory=list)
    notes: str = ""


# ─── 5. Itinerary Agent Outputs ──────────────────────────────────────────

class ItineraryAgentOutput(BaseModel):
    trip_title: str
    summary: str
    days: List[DayPlan] = Field(default_factory=list)
    travel_tips: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
