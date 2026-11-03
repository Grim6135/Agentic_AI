"""
TRIPPY Backend — CrewAI Crew Orchestrator

Defines the multi-agent Crew structure and workflow executing the
five specialist agents (Destination, Transport, Stay & Activity,
Budget, and Itinerary) with deterministic budget refinement and
resilient error handling.
"""

import uuid
from typing import Any, List, Optional
from app.agents.budget import BudgetAgent
from app.agents.destination import DestinationAgent
from app.agents.itinerary import ItineraryAgent
from app.agents.stay_activity import StayActivityAgent
from app.agents.transport import TransportAgent
from app.integrations import route_service, weather_service
from app.rag import rag_service
from app.schemas.trip import TripPreferences, TripResult
from app.tools.budget_tools import calculate_itemized_budget


class TrippyCrew:
    """
    CrewAI Orchestrator managing the five specialist agents:
    1. Destination Agent
    2. Transport Agent
    3. Stay & Activity Agent
    4. Budget Agent
    5. Itinerary Agent
    """

    def __init__(self):
        self.destination_agent = DestinationAgent()
        self.transport_agent = TransportAgent()
        self.stay_activity_agent = StayActivityAgent()
        self.budget_agent = BudgetAgent()
        self.itinerary_agent = ItineraryAgent()

    @property
    def agents(self) -> List[Any]:
        """Returns all registered specialist agents in the crew."""
        return [
            self.destination_agent,
            self.transport_agent,
            self.stay_activity_agent,
            self.budget_agent,
            self.itinerary_agent,
        ]

    def as_crewai_crew(self) -> dict:
        """
        Exports the crew configuration as a CrewAI-compliant definition
        specifying agents, tasks, and sequential execution pipeline.
        """
        return {
            "agents": [ag.as_crewai_agent() for ag in self.agents],
            "process": "sequential",
            "verbose": True,
            "tasks": [
                {"name": "Select & Rank Destinations", "agent": "Destination Specialist"},
                {"name": "Estimate Transit & Corridors", "agent": "Transport Specialist"},
                {"name": "Curate Lodging & Activities", "agent": "Stay & Activity Specialist"},
                {"name": "Validate & Optimize Itemized Budget", "agent": "Budget Specialist"},
                {"name": "Synthesize Day-by-Day Itinerary", "agent": "Itinerary Specialist"},
            ],
        }

    def as_adk_workflow(self):
        """
        Exports the Google Agent Development Kit (ADK) Workflow representation.
        """
        from app.agents.adk_adapter import adk_workflow_service
        return adk_workflow_service.build_workflow()

    async def kickoff(self, preferences: TripPreferences) -> TripResult:
        """
        Executes the full TRIPPY agent planning workflow:
        1. Validate user preferences.
        2. Retrieve RAG guide context for preferences.
        3. Destination Agent ranks candidates and selects destination.
        4. Retrieve destination-specific RAG guide context for Stay & Activity Agent.
        5. Fetch live/fallback weather and route integration estimates.
        6. Transport Agent & Stay/Activity Agent calculate baseline estimates.
        7. Budget calculated deterministically in Python.
        8. If over budget: Budget Agent proposes reductions, with up to 2 refinement attempts.
        9. Itinerary Agent synthesizes day-by-day plan.
        10. Return full TripResult with source metadata, weather, and routing.
        """
        # 1. Validation
        if preferences.end_date <= preferences.start_date:
            raise ValueError("Trip end date must be after start date.")

        # 2. RAG Retrieval for Destination Matchmaking
        pref_query = f"{preferences.travel_style.value} " + " ".join(preferences.interests)
        dest_passages = []
        try:
            dest_passages = rag_service.retrieve(query=pref_query, top_k=3)
        except Exception:
            dest_passages = []

        # 3. Step 1: Destination Agent (with RAG context)
        dest_output = await self.destination_agent.run(preferences, rag_passages=dest_passages)
        selected_dest = dest_output.selected_destination

        # 4. RAG Retrieval for Selected Destination Details
        stay_passages = []
        city_prefix = selected_dest.split(",")[0].strip().lower()
        try:
            stay_query = f"{city_prefix} lodging hotels activities dining etiquette"
            stay_passages = rag_service.retrieve(query=stay_query, destination=selected_dest, top_k=4)
        except Exception:
            stay_passages = []

        # Only retain guidebook passages that explicitly belong to this destination
        matching_passages = [
            p for p in (stay_passages + dest_passages)
            if p.destination and (
                city_prefix in p.destination.lower()
                or p.destination.lower() in selected_dest.lower()
            )
        ]
        rag_sources = list(dict.fromkeys(p.source for p in matching_passages if p.source))
        destination_guidance = [
            f"[{p.section}] {p.text.strip()} (Source: {p.source})"
            for p in matching_passages[:5]
        ]

        # 5. External Integrations: Weather & Route Estimates
        weather_res = None
        try:
            weather_res = await weather_service.get_forecast(
                destination=selected_dest,
                start_date=preferences.start_date,
                end_date=preferences.end_date,
            )
        except Exception:
            weather_res = None

        route_res = None
        try:
            route_res = await route_service.get_route(
                origin=preferences.origin,
                destination=selected_dest,
                mode=preferences.preferred_transport.value,
            )
        except Exception:
            route_res = None

        # 6. Step 2: Initial Estimates (Refinement Level 0)
        refinement_level = 0
        transport_output = await self.transport_agent.run(
            preferences, selected_dest, refinement_level=refinement_level
        )
        stay_output = await self.stay_activity_agent.run(
            preferences,
            selected_dest,
            refinement_level=refinement_level,
            rag_passages=stay_passages,
        )

        # 7. Step 3: Deterministic Budget Calculation in Python
        breakdown = calculate_itemized_budget(
            transport_cost=transport_output.total_cost,
            accommodation_cost=stay_output.total_accommodation_cost,
            activities_cost=stay_output.total_activities_cost,
            food_cost=stay_output.total_food_cost,
            currency=preferences.currency,
        )

        initial_total = breakdown.total
        budget_output = await self.budget_agent.run(
            breakdown=breakdown,
            budget_max=preferences.budget_max,
            currency=preferences.currency,
        )

        # 8. Step 4: Refinement Loop (Maximum 2 attempts if over budget)
        max_refinements = 2
        while not budget_output.is_within_budget and refinement_level < max_refinements:
            refinement_level += 1

            # Obtain cheaper alternatives based on refinement level
            transport_output = await self.transport_agent.run(
                preferences, selected_dest, refinement_level=refinement_level
            )
            stay_output = await self.stay_activity_agent.run(
                preferences,
                selected_dest,
                refinement_level=refinement_level,
                rag_passages=stay_passages,
            )

            # Deterministic recalculation in Python
            breakdown = calculate_itemized_budget(
                transport_cost=transport_output.total_cost,
                accommodation_cost=stay_output.total_accommodation_cost,
                activities_cost=stay_output.total_activities_cost,
                food_cost=stay_output.total_food_cost,
                currency=preferences.currency,
            )

            # Re-validate with Budget Agent
            budget_output = await self.budget_agent.run(
                breakdown=breakdown,
                budget_max=preferences.budget_max,
                currency=preferences.currency,
            )

        # Determine budget warnings / alternatives
        budget_warning: Optional[str] = None
        curr_sym = "₹" if preferences.currency.upper() == "INR" else ("€" if preferences.currency.upper() == "EUR" else ("£" if preferences.currency.upper() == "GBP" else "$"))
        if not budget_output.is_within_budget:
            savings = round(initial_total - breakdown.total, 2)
            alt_dest = (
                dest_output.candidates[1].name
                if len(dest_output.candidates) > 1
                else "nearby regional destination"
            )
            budget_warning = (
                f"Budget Advisory: Total cost of {curr_sym}{breakdown.total:.2f} {preferences.currency} "
                f"exceeds your limit of {curr_sym}{preferences.budget_max:.2f} by {curr_sym}{budget_output.overflow_amount:.2f}. "
                f"Two optimization cycles were applied (saving {curr_sym}{savings:.2f}). "
                f"Recommended alternatives: shift dates by 1-2 weeks, shorten duration, "
                f"or consider budget destination '{alt_dest}'."
            )

        # 9. Step 5: Itinerary Agent (synthesize final plan with live weather & route context)
        itinerary_output = await self.itinerary_agent.run(
            preferences=preferences,
            destination=selected_dest,
            transport=transport_output,
            stay_activity=stay_output,
            budget=budget_output,
            budget_warning=budget_warning,
            weather=weather_res,
            route=route_res,
        )

        # 10. Assemble final TripResult
        trip_id = f"trip_{uuid.uuid4().hex[:10]}"
        all_destinations = [selected_dest]
        if preferences.destinations:
            all_destinations = preferences.destinations

        return TripResult(
            trip_id=trip_id,
            preferences=preferences,
            destinations=all_destinations,
            currency=preferences.currency,
            itinerary=itinerary_output.days,
            budget=breakdown,
            summary=itinerary_output.summary,
            warnings=itinerary_output.warnings,
            weather=weather_res,
            route_estimate=route_res,
            rag_sources=rag_sources,
            destination_guidance=destination_guidance,
        )

