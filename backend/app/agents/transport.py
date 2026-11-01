"""
TRIPPY Backend — Transport Agent

Agent 2: Transport Specialist.
Estimates transport cost, routes, durations, and cost-reduction alternatives.
"""

from app.agents.base import TrippyAgent
from app.schemas.agent_outputs import TransportAgentOutput
from app.schemas.trip import TripPreferences
from app.services.llm_provider import llm_service
from app.tools.transport_tools import estimate_transport


class TransportAgent(TrippyAgent):
    """Transport Specialist responsible for estimating transit legs and costs."""

    def __init__(self):
        super().__init__(
            role="Transport Specialist",
            goal="Estimate transport cost and duration using supported data, routing modes, and realistic options.",
            backstory=(
                "Global transit logistics and route planning specialist. Expert at comparing flights, "
                "high-speed trains, scenic rail, and road connections to balance comfort, travel time, and cost."
            ),
            tools=[estimate_transport],
        )

    async def run(
        self,
        preferences: TripPreferences,
        destination: str,
        refinement_level: int = 0,
    ) -> TransportAgentOutput:
        """
        Calculates transport estimates between origin and destination.
        refinement_level: 0 (default), 1 (economy saver), 2 (deep budget).
        """
        deterministic_output = estimate_transport(
            origin=preferences.origin,
            destination=destination,
            preferred_mode=preferences.preferred_transport,
            travelers=preferences.travelers,
            travel_style=preferences.travel_style,
            refinement_level=refinement_level,
        )

        if llm_service.is_available() and refinement_level == 0:
            try:
                prompt = (
                    f"Estimate transport from {preferences.origin} to {destination} for {preferences.travelers} traveler(s).\n"
                    f"Mode: {preferences.preferred_transport.value}. Style: {preferences.travel_style.value}.\n"
                    f"Baseline total estimate: ${deterministic_output.total_cost:.2f} {preferences.currency}."
                )
                system = f"You are the {self.role}. {self.backstory}"
                ai_res = await llm_service.generate_structured(prompt, system, TransportAgentOutput)
                if ai_res and ai_res.legs:
                    return ai_res
            except Exception:
                pass

        return deterministic_output
