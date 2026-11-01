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

        # 1. Fetch live real-world landmarks and currency exchange rate
        landmarks_list = []
        live_rate = None
        try:
            from app.integrations.places import places_service
            place_info = await places_service.get_destination_info(destination)
            if place_info and place_info.landmarks:
                landmarks_list = [lm.name for lm in place_info.landmarks]
        except Exception:
            pass

        try:
            from app.integrations.forex import forex_service
            live_rate = await forex_service.get_multiplier_from_usd(preferences.currency)
        except Exception:
            pass

        deterministic_output = recommend_stays_and_activities(
            destination=destination,
            travel_style=preferences.travel_style,
            start_date=preferences.start_date,
            duration_days=duration_days,
            travelers=preferences.travelers,
            interests=preferences.interests,
            refinement_level=refinement_level,
            currency=preferences.currency,
            live_forex_rate=live_rate,
            landmarks=landmarks_list,
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
                curr_sym = "₹" if preferences.currency.upper() == "INR" else ("€" if preferences.currency.upper() == "EUR" else ("£" if preferences.currency.upper() == "GBP" else "$"))
                poi_snippet = f"Verified local landmarks (Wikipedia Geosearch): {', '.join(landmarks_list[:6])}.\n" if landmarks_list else ""
                rate_snippet = f"Live Forex: 1 USD = {live_rate:.2f} {preferences.currency.upper()}.\n" if live_rate else ""

                prompt = (
                    f"Curate authentic accommodation, daily activities, and dining in {destination} for a {duration_days}-day trip.\n"
                    f"Style: {preferences.travel_style.value}. Travelers: {preferences.travelers}. Currency: {preferences.currency.upper()} ({curr_sym}).\n"
                    f"Interests: {preferences.interests}.\n"
                    f"{poi_snippet}"
                    f"{rate_snippet}"
                    f"CRITICAL: 'activities' MUST contain exactly {duration_days} items (one primary activity per day of the trip).\n"
                    f"CRITICAL: All prices (cost_per_night, total_accommodation_cost, cost_estimate, daily_food_cost, total_food_cost) MUST be in {preferences.currency.upper()} ({curr_sym}) with realistic local rates for {destination}.\n"
                    f"Baseline reference: {deterministic_output.accommodation_name} ({curr_sym}{deterministic_output.cost_per_night:.2f}/night)."
                )
                system = f"You are the {self.role}. {self.backstory}"
                ai_res = await llm_service.generate_structured(prompt, system, StayActivityAgentOutput)
                if ai_res and ai_res.activities:
                    if len(ai_res.activities) > duration_days:
                        ai_res.activities = ai_res.activities[:duration_days]
                    elif len(ai_res.activities) < duration_days:
                        needed = duration_days - len(ai_res.activities)
                        ai_res.activities.extend(deterministic_output.activities[:needed])
                    return ai_res
            except Exception:
                pass

        return deterministic_output
