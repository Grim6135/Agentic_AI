"""
TRIPPY Backend — Budget Tools

Pure deterministic Python budget calculator, cost limit validator,
and actionable reduction generator.
"""

from typing import List, Optional
from app.schemas.agent_outputs import BudgetAgentOutput, BudgetReductionProposal
from app.schemas.trip import BudgetBreakdown


def calculate_itemized_budget(
    transport_cost: float,
    accommodation_cost: float,
    activities_cost: float,
    food_cost: float,
    misc_rate: float = 0.08,
) -> BudgetBreakdown:
    """
    Deterministically computes itemized budget breakdown with contingency.
    """
    transport = round(max(0.0, transport_cost), 2)
    accommodation = round(max(0.0, accommodation_cost), 2)
    activities = round(max(0.0, activities_cost), 2)
    food = round(max(0.0, food_cost), 2)

    subtotal = transport + accommodation + activities + food
    misc = round(subtotal * misc_rate, 2)
    total = round(subtotal + misc, 2)

    return BudgetBreakdown(
        transport=transport,
        accommodation=accommodation,
        activities=activities,
        food_estimate=food,
        miscellaneous=misc,
        total=total,
    )


def evaluate_budget(
    breakdown: BudgetBreakdown,
    budget_max: Optional[float],
    currency: str = "USD",
) -> BudgetAgentOutput:
    """
    Validates total calculated cost against traveler's budget limit.
    Generates actionable reduction proposals if cost exceeds budget_max.
    """
    if budget_max is None or budget_max <= 0:
        return BudgetAgentOutput(
            breakdown=breakdown,
            budget_max=budget_max,
            is_within_budget=True,
            overflow_amount=0.0,
            reduction_proposals=[],
            notes="No maximum budget constraint specified. Plan validated.",
        )

    is_within = breakdown.total <= budget_max
    overflow = max(0.0, round(breakdown.total - budget_max, 2))

    proposals: List[BudgetReductionProposal] = []

    if not is_within:
        # 1. Accommodation proposal (usually highest flexible lever)
        if breakdown.accommodation > 0:
            est_acc_savings = round(breakdown.accommodation * 0.35, 2)
            proposals.append(
                BudgetReductionProposal(
                    category="accommodation",
                    action="Shift to standard/guesthouse tier accommodation",
                    estimated_savings=est_acc_savings,
                    description=f"Switching accommodation tier saves ~${est_acc_savings:.2f} {currency}.",
                )
            )

        # 2. Transport proposal
        if breakdown.transport > 0:
            est_trans_savings = round(breakdown.transport * 0.20, 2)
            proposals.append(
                BudgetReductionProposal(
                    category="transport",
                    action="Switch to economy saver / off-peak transit timing",
                    estimated_savings=est_trans_savings,
                    description=f"Booking off-peak or saver transit saves ~${est_trans_savings:.2f} {currency}.",
                )
            )

        # 3. Activities proposal
        if breakdown.activities > 0:
            est_act_savings = round(breakdown.activities * 0.40, 2)
            proposals.append(
                BudgetReductionProposal(
                    category="activities",
                    action="Substitute paid excursions with free cultural landmarks",
                    estimated_savings=est_act_savings,
                    description=f"Self-guided walks and municipal museums save ~${est_act_savings:.2f} {currency}.",
                )
            )

        # 4. Food proposal
        if breakdown.food_estimate > 0:
            est_food_savings = round(breakdown.food_estimate * 0.25, 2)
            proposals.append(
                BudgetReductionProposal(
                    category="food",
                    action="Focus on local bistros, street markets, and included breakfasts",
                    estimated_savings=est_food_savings,
                    description=f"Casual dining saves ~${est_food_savings:.2f} {currency}.",
                )
            )

        notes = (
            f"Trip total of ${breakdown.total:.2f} exceeds limit of ${budget_max:.2f} "
            f"by ${overflow:.2f} {currency}. {len(proposals)} reduction strategies proposed."
        )
    else:
        notes = (
            f"Trip total of ${breakdown.total:.2f} {currency} is fully within the "
            f"maximum budget limit of ${budget_max:.2f} (surplus: ${budget_max - breakdown.total:.2f})."
        )

    return BudgetAgentOutput(
        breakdown=breakdown,
        budget_max=budget_max,
        is_within_budget=is_within,
        overflow_amount=overflow,
        reduction_proposals=proposals,
        notes=notes,
    )
