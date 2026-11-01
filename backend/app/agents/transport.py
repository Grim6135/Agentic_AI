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
            currency=preferences.currency,
        )

        if llm_service.is_available() and refinement_level == 0:
            try:
                curr_sym = "₹" if preferences.currency.upper() == "INR" else ("€" if preferences.currency.upper() == "EUR" else ("£" if preferences.currency.upper() == "GBP" else "$"))
                prompt = (
                    f"Estimate realistic round-trip transit from {preferences.origin} to {destination} for {preferences.travelers} traveler(s).\n"
                    f"Mode: {preferences.preferred_transport.value}. Style: {preferences.travel_style.value}.\n"
                    f"Currency: {preferences.currency.upper()} ({curr_sym}).\n"
                    f"CRITICAL: 'legs' MUST contain exactly 2 TransportLeg items: one outbound leg ({preferences.origin} -> {destination}) "
                    f"and one return leg ({destination} -> {preferences.origin}).\n"
                    f"CRITICAL: All cost_estimate and total_cost numbers MUST be in {preferences.currency.upper()} ({curr_sym}) representing realistic fares.\n"
                    f"Baseline estimate: {curr_sym}{deterministic_output.total_cost:.2f} {preferences.currency}."
                )
                system = f"You are the {self.role}. {self.backstory}"
                ai_res = await llm_service.generate_structured(prompt, system, TransportAgentOutput)
                if ai_res and ai_res.legs:
                    if len(ai_res.legs) == 1:
                        # Auto-mirror return leg if LLM only provided outbound leg
                        outbound = ai_res.legs[0]
                        from app.schemas.trip import TransportLeg
                        return_leg = TransportLeg(
                            mode=outbound.mode,
                            origin=outbound.destination,
                            destination=outbound.origin,
                            departure_time="Return date afternoon",
                            arrival_time="Return date evening",
                            cost_estimate=outbound.cost_estimate,
                            notes=f"Return leg ({outbound.destination} to {outbound.origin})",
                        )
                        ai_res.legs.append(return_leg)
                        ai_res.total_cost = round(outbound.cost_estimate * 2, 2)
                    if len(ai_res.legs) == 2:
                        return ai_res
            except Exception:
                pass

        return deterministic_output
