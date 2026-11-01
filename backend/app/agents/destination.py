"""
TRIPPY Backend — Destination Agent

Agent 1: Destination Specialist.
Ranks destinations using preferences, duration, budget, and travel style.
"""

from typing import Optional
from app.agents.base import TrippyAgent
from app.schemas.agent_outputs import DestinationAgentOutput
from app.schemas.trip import TripPreferences
from app.services.llm_provider import llm_service
from app.tools.destination_tools import rank_destination_candidates


class DestinationAgent(TrippyAgent):
    """Destination Specialist that selects and ranks travel candidates."""

    def __init__(self):
        super().__init__(
            role="Destination Specialist",
            goal="Analyze traveler preferences, duration, style, and budget to select and rank optimal destination candidates.",
            backstory=(
                "Senior travel curator with 15+ years of global travel matchmaking experience. "
                "Master at uncovering destinations that balance personal interests, optimal timing, and budget constraints."
            ),
            tools=[rank_destination_candidates],
        )

    async def run(
        self,
        preferences: TripPreferences,
        rag_passages: Optional[list] = None,
    ) -> DestinationAgentOutput:
        """
        Executes destination matchmaking workflow with optional RAG passage context.
        """
        duration_days = max(1, (preferences.end_date - preferences.start_date).days)

        # 1. Deterministic baseline candidates via tool
        candidates = rank_destination_candidates(
            origin=preferences.origin,
            requested_destinations=preferences.destinations,
            travel_style=preferences.travel_style,
            duration_days=duration_days,
            budget_max=preferences.budget_max,
            interests=preferences.interests,
        )

        selected = candidates[0].name if candidates else (preferences.destinations[0] if preferences.destinations else "Kyoto, Japan")
        rationale = (
            f"Selected {selected} based on top match score for {preferences.travel_style.value} style, "
            f"aligning with {', '.join(preferences.interests) if preferences.interests else 'curated highlights'}."
        )

        # Incorporate RAG guidebook insights if available
        if rag_passages:
            matching_passage = next(
                (p for p in rag_passages if selected.split(",")[0].lower() in p.destination.lower()),
                rag_passages[0],
            )
            rationale += f" Guidance supported by {matching_passage.source} ({matching_passage.section})."
            if candidates:
                candidates[0].why_matched += f" [Source: {matching_passage.source}]"

        deterministic_output = DestinationAgentOutput(
            selected_destination=selected,
            candidates=candidates,
            rationale=rationale,
        )

        # 2. If AI provider available, optionally refine narrative
        if llm_service.is_available():
            try:
                prompt = (
                    f"Traveler from {preferences.origin} planning a {duration_days}-day {preferences.travel_style.value} trip.\n"
                    f"Interests: {preferences.interests}.\n"
                    f"Budget max: {preferences.budget_max} {preferences.currency}.\n"
                    f"Top candidate: {selected}.\n"
                    f"Provide refined destination evaluation and rationale."
                )
                system = f"You are the {self.role}. {self.backstory}"
                ai_res = await llm_service.generate_structured(prompt, system, DestinationAgentOutput)
                if ai_res and ai_res.candidates:
                    return ai_res
            except Exception:
                pass

        return deterministic_output
