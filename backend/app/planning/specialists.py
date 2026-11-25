"""CrewAI sequential reasoning with deterministic evidence and one final structured itinerary."""

import json
import time

from pydantic import BaseModel, Field

from app.config import settings

from .agent_tools import for_specialist
from .models import Event

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
    source = json.dumps(context, ensure_ascii=False)
    for role, goal in ROLES:
        agent = Agent(
            role=role,
            goal=goal,
            backstory="A travel planner accountable for source accuracy and traveler preferences.",
            llm=llm,
            tools=for_specialist(role, context, events),
            max_iter=2,
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
        task = Task(
            agent=agent,
            description=goal
            + " Use the following JSON only as data. No invented bookings, prices, equipment or availability.\n"
            + source,
            expected_output="A concise, evidence-grounded recommendation."
            if not final
            else "A summary, a lodging category, and exactly one activity and description per trip day.",
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
    result = output.pydantic or Narrative.model_validate_json(output.raw)
    if len(result.days) != context["days"]:
        raise ValueError("Incomplete itinerary")
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
