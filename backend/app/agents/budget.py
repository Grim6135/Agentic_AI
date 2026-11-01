"""
TRIPPY Backend — Budget Agent

Agent 4: Budget Specialist.
Validates itemized costs deterministically and proposes specific reductions.
"""

from typing import Optional
from app.agents.base import TrippyAgent
from app.schemas.agent_outputs import BudgetAgentOutput
from app.schemas.trip import BudgetBreakdown
from app.services.llm_provider import llm_service
from app.tools.budget_tools import calculate_itemized_budget, evaluate_budget


class BudgetAgent(TrippyAgent):
    """Budget Specialist responsible for cost validation and reduction strategies."""

    def __init__(self):
        super().__init__(
            role="Budget Specialist",
            goal="Validate itemized costs against user limits and propose specific actionable reductions.",
            backstory=(
                "Travel finance strategist and consumer budget optimizer. "
                "Ensures every dollar spent maximizes traveler satisfaction while strictly enforcing cost limits."
            ),
            tools=[calculate_itemized_budget, evaluate_budget],
        )

    async def run(
        self,
        breakdown: BudgetBreakdown,
        budget_max: Optional[float],
        currency: str = "USD",
    ) -> BudgetAgentOutput:
        """
        Validates budget and generates actionable reductions if over budget.
        Calculations are strictly deterministic in Python.
        """
        # Deterministic evaluation is always the ground truth
        deterministic_output = evaluate_budget(
            breakdown=breakdown,
            budget_max=budget_max,
            currency=currency,
        )

        if llm_service.is_available() and not deterministic_output.is_within_budget:
            try:
                curr_sym = "₹" if currency.upper() == "INR" else ("€" if currency.upper() == "EUR" else ("£" if currency.upper() == "GBP" else "$"))
                prompt = (
                    f"Trip costs {curr_sym}{breakdown.total:.2f} {currency}, exceeding budget limit of {curr_sym}{budget_max:.2f}.\n"
                    f"Breakdown ({currency}): Transport: {curr_sym}{breakdown.transport:.2f}, Lodging: {curr_sym}{breakdown.accommodation:.2f}, "
                    f"Activities: {curr_sym}{breakdown.activities:.2f}, Food: {curr_sym}{breakdown.food_estimate:.2f}.\n"
                    f"Provide refined reduction analysis while preserving deterministic calculations."
                )
                system = f"You are the {self.role}. {self.backstory}"
                ai_res = await llm_service.generate_structured(prompt, system, BudgetAgentOutput)
                if ai_res and ai_res.reduction_proposals:
                    # Ensure deterministic math is never overwritten by AI
                    ai_res.breakdown = breakdown
                    ai_res.is_within_budget = deterministic_output.is_within_budget
                    ai_res.overflow_amount = deterministic_output.overflow_amount
                    return ai_res
            except Exception:
                pass

        return deterministic_output
