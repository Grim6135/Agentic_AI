"""
TRIPPY Backend — Stay & Activity Agent

Agent 3: Stay & Activity Specialist.
Recommends accommodation categories, activities and food.
"""

from app.agents.base import TrippyAgent
from app.schemas.agent_outputs import StayActivityAgentOutput
from app.schemas.trip import TripPreferences
from app.services.llm_provider import llm_service
from app.tools.stay_activity_tools import recommend_stays_and_activities


class StayActivityAgent(TrippyAgent):
    """Stay & Activity Specialist recommending accommodations, activities, and dining."""

    def __init__(self):
        super().__init__(
            role="Stay & Activity Specialist",
            goal="Recommend accommodation categories, curated daily activities, and food budgets matching travel style and tier.",
            backstory=(
                "Boutique hospitality director and local experience curator. "
                "Known for selecting character-rich hotels and authentic cultural, culinary, and outdoor activities."
            ),
            tools=[recommend_stays_and_activities],
        )

    async def run(
        self,
        preferences: TripPreferences,
        destination: str,
        refinement_level: int = 0,
        rag_passages: Optional[list] = None,
    ) -> StayActivityAgentOutput:
        """
        Recommends stays, activities, and food budget with optional RAG context.
        refinement_level: 0 (default), 1 (midscale saver), 2 (deep budget).
        """
        duration_days = max(1, (preferences.end_date - preferences.start_date).days)

        deterministic_output = recommend_stays_and_activities(
            destination=destination,
            travel_style=preferences.travel_style,
            start_date=preferences.start_date,
            duration_days=duration_days,
            travelers=preferences.travelers,
            interests=preferences.interests,
            refinement_level=refinement_level,
            currency=preferences.currency,
        )

        # Incorporate RAG guidebook tips
        if rag_passages:
            for passage in rag_passages[:2]:
                deterministic_output.food_highlights.append(
                    f"Guidebook tip: {passage.section} — {passage.text[:90]}… [Source: {passage.source}]"
                )
                if deterministic_output.activities:
                    # Enrich first activity description with guidebook reference
                    deterministic_output.activities[0].description += f" (Curated via {passage.source})"

        if llm_service.is_available() and refinement_level == 0:
            try:
                prompt = (
                    f"Curate stay, activities, and food in {destination} for a {duration_days}-day trip.\n"
                    f"Style: {preferences.travel_style.value}. Travelers: {preferences.travelers}.\n"
                    f"Interests: {preferences.interests}.\n"
                    f"Baseline accommodation: {deterministic_output.accommodation_name} "
                    f"(${deterministic_output.cost_per_night:.2f}/night)."
                )
                system = f"You are the {self.role}. {self.backstory}"
                ai_res = await llm_service.generate_structured(prompt, system, StayActivityAgentOutput)
                if ai_res and ai_res.activities:
                    return ai_res
            except Exception:
                pass

        return deterministic_output
