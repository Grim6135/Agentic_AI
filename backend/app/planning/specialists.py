"""CrewAI sequential reasoning with deterministic evidence and one final structured itinerary."""

import json
import time

from pydantic import BaseModel, Field

from app.config import settings

from .agent_tools import for_specialist
from .models import Event, clean

ROLES = (
    (
        "Destination Specialist",
        "Explain the destination using only the supplied research and guide records.",
    ),
    (
        "Transport Specialist",
        "Assess the requested mode, the route evidence and the group's transport allowance.",
    ),
    (
        "Stay & Activity Specialist",
        "Suggest accommodation categories and feasible daily activities. Distinguish suggestions from confirmed facts.",
    ),
    (
        "Budget Specialist",
        "Review the supplied group budget and affordability. Preserve the audited numbers. Explain uncertainty.",
    ),
    (
        "Itinerary Specialist",
        "Combine the handoffs into a practical itinerary covering every requested day.",
    ),
)


class PlannedDay(BaseModel):
    activity: str = Field(min_length=1, max_length=180)
    description: str = Field(min_length=1, max_length=600)


class Narrative(BaseModel):
    summary: str = Field(min_length=1, max_length=1200)
    lodging_category: str = Field(min_length=1, max_length=120)
    days: list[PlannedDay] = Field(min_length=1, max_length=30)


def _extract_narrative(output, default_destination="Destination", num_days=1) -> Narrative:
    if getattr(output, "pydantic", None) and isinstance(output.pydantic, Narrative):
        return output.pydantic
    raw = getattr(output, "raw", "") or str(output)
    raw = raw.strip()
    candidate = raw
    if "```" in candidate:
        import re
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", candidate, re.DOTALL)
        if match:
            candidate = match.group(1).strip()
    if "{" in candidate and "}" in candidate:
        start = candidate.find("{")
        end = candidate.rfind("}") + 1
        candidate = candidate[start:end]
    try:
        return Narrative.model_validate_json(candidate)
    except Exception:
        pass

    import re
    summary = ""
    lodging = "Boutique & Luxury Lodging"
    days_list = []

    sum_match = re.search(r"(?:Summary|Overview):\s*(.*?)(?=(?:Lodging|Accommodation|Day 1|\n\n[A-Z]))", raw, re.DOTALL | re.IGNORECASE)
    if sum_match:
        summary = sum_match.group(1).strip()
    elif len(raw.splitlines()) > 0:
        summary = raw.splitlines()[0].strip()

    lodge_match = re.search(r"(?:Lodging Category|Lodging|Accommodation):\s*(.*?)(?=(?:Day 1|\n\n[A-Z]))", raw, re.DOTALL | re.IGNORECASE)
    if lodge_match:
        lodging = lodge_match.group(1).strip()[:115]

    day_blocks = re.split(r"(?:^|\n)(?:###\s*)?Day\s*(\d+)[:\s-]*", raw, flags=re.IGNORECASE)
    if len(day_blocks) > 1:
        for i in range(1, len(day_blocks), 2):
            d_num = day_blocks[i]
            d_content = day_blocks[i + 1].strip() if i + 1 < len(day_blocks) else ""
            act_match = re.search(r"Activity:\s*(.*?)(?=(?:Description:|$|\n))", d_content, re.IGNORECASE)
            desc_match = re.search(r"Description:\s*(.*?)$", d_content, re.DOTALL | re.IGNORECASE)
            act = act_match.group(1).strip() if act_match else f"Day {d_num} in {default_destination}"
            desc = desc_match.group(1).strip() if desc_match else d_content[:500] or f"Explore {default_destination} attractions."
            days_list.append(PlannedDay(activity=act[:175], description=desc[:590]))

    if not summary:
        summary = f"Custom {num_days}-day itinerary in {default_destination}."
    if not days_list:
        for d in range(1, num_days + 1):
            days_list.append(PlannedDay(activity=f"Day {d} in {default_destination}", description=f"Explore highlights and culture of {default_destination}."))

    return Narrative(summary=summary[:1190], lodging_category=lodging[:115], days=days_list)


def specialist_model():
    if settings.crew_model.startswith("groq/"):
        from .groq_model import GroqChat
        return GroqChat(settings.crew_model, settings.model_key(settings.crew_model))
    from crewai import LLM
    return LLM(model=settings.crew_model, api_key=settings.model_key(settings.crew_model), timeout=25, max_retries=0, temperature=0)


def run_specialists(context: dict):
    from crewai import Agent, Crew, Process, Task

    llm = specialist_model()
    agents, tasks, events = [], [], []
    started = time.monotonic()

    city = context.get("destination", "Destination")
    p = context.get("preferences", {})
    budget = context.get("budget_estimate", {})
    route = context.get("route") or {}
    weather = context.get("weather") or {}
    places = context.get("places", [])
    places_str = ", ".join(places[:6]) if places else f"key attractions across {city}"
    hotel = context.get("hotel", "curated accommodations")
    days = context.get("days", 1)
    travelers = p.get("travelers", 1) if isinstance(p, dict) else getattr(p, "travelers", 1)
    origin = p.get("origin", "Origin") if isinstance(p, dict) else getattr(p, "origin", "Origin")
    mode = p.get("preferred_transport", "transit") if isinstance(p, dict) else getattr(p, "preferred_transport", "transit")
    interests_raw = p.get("interests", []) if isinstance(p, dict) else getattr(p, "interests", [])
    interests_str = ", ".join(interests_raw) if interests_raw else "local culture and sightseeing"

    role_prompts = {
        "Destination Specialist": (
            f"Summarize destination highlights and culture for {city} using verified attractions: {places_str}. "
            f"Context: {clean(context.get('research', ''))[:300]}"
        ),
        "Transport Specialist": (
            f"Assess transit from {origin} to {city} ({mode}) based on route distance: "
            f"{route.get('distance_km', 'regional')}km (~{route.get('duration_hours', 'direct')}h)."
        ),
        "Stay & Activity Specialist": (
            f"Review group stay at {hotel} and daily activities in {city} under weather: "
            f"{weather.get('condition', 'seasonal')} ({weather.get('temperature_c', 'comfortable')}°C)."
        ),
        "Budget Specialist": (
            f"Review group budget for {travelers} traveler(s): Transport={budget.get('transport', 0)}, "
            f"Lodging={budget.get('accommodation', 0)}, Activities={budget.get('activities', 0)}, "
            f"Food={budget.get('food_estimate', 0)}, Total={budget.get('total', 0)} {budget.get('currency', 'USD')}."
        ),
        "Itinerary Specialist": (
            f"Create a comprehensive {days}-day itinerary for {city} honoring the specialists' handoffs. "
            f"Lodging: {hotel}. Featured attractions: {places_str}. Traveler interests: {interests_str}. "
            f"Output ONLY a valid JSON object matching the requested schema with no markdown code blocks:\n"
            f'{{"summary": "...", "lodging_category": "...", "days": [{{"activity": "...", "description": "..."}}]}}\n'
            f"The days array MUST contain exactly {days} items (one per trip day)."
        ),
    }

    for role, goal in ROLES:
        agent = Agent(
            role=role,
            goal=goal,
            backstory="A travel planner accountable for source accuracy and traveler preferences.",
            llm=llm,
            tools=for_specialist(role, context, events),
            max_iter=1,
            max_retry_limit=0,
            allow_delegation=False,
            verbose=False,
        )

        def completed(output, name=role):
            events.append(
                Event(
                    component="CrewAI",
                    action=name,
                    elapsed_ms=int((time.monotonic() - started) * 1000),
                )
            )

        final = role == ROLES[-1][0]
        task_desc = role_prompts[role]
        if final:
            expected = f"A valid JSON object with summary, lodging_category, and exactly {days} days."
        else:
            task_desc += "\nState your concise evidence-grounded findings (under 30 words) directly as Final Answer without calling tools."
            expected = "A concise evidence-grounded assessment under 30 words as Final Answer."

        task = Task(
            agent=agent,
            description=task_desc,
            expected_output=expected,
            callback=completed,
            **({"output_pydantic": Narrative} if final else {}),
        )
        agents.append(agent)
        tasks.append(task)
    crew = Crew(
        agents=agents,
        tasks=tasks,
        process=Process.sequential,
        verbose=False,
        memory=False,
    )
    output = crew.kickoff()
    if [e.action for e in events if e.component == "CrewAI"] != [
        role for role, _ in ROLES
    ]:
        raise RuntimeError("Incomplete specialist execution")
    result = _extract_narrative(
        output,
        default_destination=context.get("destination", "Destination"),
        num_days=context.get("days", 1),
    )
    num_days = context.get("days", len(result.days))
    while len(result.days) < num_days:
        day_num = len(result.days) + 1
        result.days.append(PlannedDay(activity=f"Explore local highlights", description=f"Spend Day {day_num} experiencing the destination's cultural landmarks, neighborhood markets, and local cuisine."))
    if len(result.days) > num_days:
        result.days = result.days[:num_days]
    usage = getattr(output, "token_usage", None)
    events.append(
        Event(
            component="CrewAI",
            action="crew completed",
            elapsed_ms=int((time.monotonic() - started) * 1000),
            tokens=getattr(usage, "total_tokens", None),
        )
    )
    return result, events
