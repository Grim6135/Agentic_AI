"""
TRIPPY Backend — Itinerary Agent

Agent 5: Itinerary Specialist.
Combines validated agent outputs into a polished day-by-day itinerary.
"""

from datetime import timedelta
from typing import List, Optional
from app.agents.base import TrippyAgent
from app.schemas.agent_outputs import (
    BudgetAgentOutput,
    ItineraryAgentOutput,
    StayActivityAgentOutput,
    TransportAgentOutput,
)
from app.schemas.trip import Accommodation, DayPlan, TripPreferences
from app.services.llm_provider import llm_service


class ItineraryAgent(TrippyAgent):
    """Itinerary Specialist combining validated outputs into a day-by-day plan."""

    def __init__(self):
        super().__init__(
            role="Itinerary Specialist",
            goal="Combine validated outputs into a polished, coherent day-by-day travel plan with scheduling and practical tips.",
            backstory=(
                "Master travel itinerary architect with expertise in pacing, daily scheduling, "
                "local logistics, and crafting unforgettable travel narratives."
            ),
            tools=[],
        )

    async def run(
        self,
        preferences: TripPreferences,
        destination: str,
        transport: TransportAgentOutput,
        stay_activity: StayActivityAgentOutput,
        budget: BudgetAgentOutput,
        budget_warning: Optional[str] = None,
    ) -> ItineraryAgentOutput:
        """
        Synthesizes validated outputs into an ItineraryAgentOutput with DayPlan items.
        """
        duration_days = max(1, (preferences.end_date - preferences.start_date).days)
        nights = max(1, duration_days - 1)

        # Build day-by-day plans
        days: List[DayPlan] = []

        hotel = Accommodation(
            name=stay_activity.accommodation_name,
            location=destination,
            check_in=preferences.start_date,
            check_out=preferences.end_date,
            cost_per_night=stay_activity.cost_per_night,
            rating=4.5 if stay_activity.accommodation_category in ["luxury", "boutique"] else 4.0,
        )

        daily_budget = round(budget.breakdown.total / duration_days, 2)

        for day_num in range(1, duration_days + 1):
            day_date = preferences.start_date + timedelta(days=day_num - 1)
            day_activities = [
                act for act in stay_activity.activities if act.date == day_date
            ]
            if not day_activities and stay_activity.activities:
                # Fallback to index-based mapping
                idx = (day_num - 1) % len(stay_activity.activities)
                day_activities = [stay_activity.activities[idx]]

            # Map transport legs to first and last day
            day_transport = []
            if day_num == 1 and transport.legs:
                day_transport.append(transport.legs[0])
            elif day_num == duration_days and len(transport.legs) > 1:
                day_transport.append(transport.legs[1])

            days.append(
                DayPlan(
                    day=day_num,
                    date=day_date,
                    activities=day_activities,
                    accommodation=hotel if day_num < duration_days else None,
                    transport=day_transport,
                    daily_budget=daily_budget,
                )
            )

        trip_title = f"{duration_days}-Day {preferences.travel_style.value.title()} Escape to {destination}"
        summary = (
            f"An immersive {duration_days}-day journey from {preferences.origin} to {destination}. "
            f"Featuring curated {stay_activity.accommodation_category} lodging at {stay_activity.accommodation_name}, "
            f"{preferences.preferred_transport.value} travel, and daily experiences tailored to your travel style."
        )

        travel_tips = [
            f"Carry local currency and a no-foreign-transaction-fee credit card.",
            f"Download offline maps of {destination} before departure.",
            f"Keep digital copies of booking confirmations and transport passes.",
        ]

        warnings: List[str] = []
        if budget_warning:
            warnings.append(budget_warning)

        deterministic_output = ItineraryAgentOutput(
            trip_title=trip_title,
            summary=summary,
            days=days,
            travel_tips=travel_tips,
            warnings=warnings,
        )

        # AI narrative enhancement if available
        if llm_service.is_available():
            try:
                prompt = (
                    f"Enhance the title and summary for a {duration_days}-day trip to {destination}.\n"
                    f"Style: {preferences.travel_style.value}. Travelers: {preferences.travelers}.\n"
                    f"Summary draft: {summary}"
                )
                system = f"You are the {self.role}. {self.backstory}"
                ai_res = await llm_service.generate_structured(prompt, system, ItineraryAgentOutput)
                if ai_res and ai_res.days:
                    # Ensure verified DayPlan structure remains valid
                    if not ai_res.warnings and warnings:
                        ai_res.warnings = warnings
                    return ai_res
            except Exception:
                pass

        return deterministic_output
