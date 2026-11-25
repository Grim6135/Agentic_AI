"""Run actual SDK orchestration with controlled model and data-provider responses."""

import json

import pytest


@pytest.mark.anyio
async def test_adk_runner_invokes_tool_and_callbacks(monkeypatch):
    from app.adk_service import server
    from app.schemas.trip import TripPreferences
    from google.adk.models.base_llm import BaseLlm
    from google.adk.models.llm_response import LlmResponse
    from google.genai import types

    class FixtureModel(BaseLlm):
        async def generate_content_async(self, llm_request, stream=False):
            seen = any(
                part.function_response
                for message in llm_request.contents
                for part in message.parts or []
            )
            part = (
                types.Part(text="Research finished.")
                if seen
                else types.Part(
                    function_call=types.FunctionCall(
                        name="research_city", args={"city": "Kyoto, Japan"}
                    )
                )
            )
            yield LlmResponse(content=types.Content(role="model", parts=[part]))

    async def coordinates(_):
        return (35.0, 135.0), "Test geocoder"

    async def places(*_):
        return None

    monkeypatch.setattr(server, "adk_model", lambda: FixtureModel(model="fixture"))
    monkeypatch.setattr("app.planning.geocode.locate", coordinates)
    monkeypatch.setattr("app.integrations.places_service.get_destination_info", places)
    prefs = TripPreferences(
        origin="Tokyo",
        destinations=["Kyoto, Japan"],
        start_date="2027-01-02",
        end_date="2027-01-03",
    )
    result = await server.research(prefs)
    assert result["destination"] == "Kyoto, Japan"
    actions = [e["action"] for e in result["events"]]
    assert actions.count("research_city") == 1
    assert actions.count("model response") == 2
    assert actions[0] == "agent started" and actions[-1] == "agent completed"


def test_crewai_executes_five_tasks(monkeypatch, tmp_path):
    from crewai_core import settings as core_settings
    monkeypatch.setattr(core_settings, "DEFAULT_CONFIG_PATH", tmp_path / "settings.json", raising=False)
    monkeypatch.setenv("CREWAI_STORAGE_DIR", str(tmp_path))
    monkeypatch.setenv("CREWAI_TRACING_ENABLED", "false")
    monkeypatch.setenv("CREWAI_DISABLE_TELEMETRY", "true")
    import crewai
    from app.planning.specialists import ROLES, run_specialists
    from crewai import BaseLLM

    class FixtureModel(BaseLLM):
        def call(
            self,
            messages,
            tools=None,
            callbacks=None,
            available_functions=None,
            **kwargs,
        ):
            result = {
                "summary": "Fixture itinerary.",
                "lodging_category": "Guesthouse",
                "days": [
                    {"activity": "Walk", "description": "Walk in the public park."}
                ],
            }
            return "Final Answer: " + json.dumps(result)

    monkeypatch.setattr(
        "app.planning.specialists.specialist_model", lambda: FixtureModel(model="test", temperature=0)
    )
    result, events = run_specialists(
        {
            "days": 1,
            "destination": "Kyoto",
            "preferences": {
                "origin": "Tokyo",
                "preferred_transport": "train",
                "start_date": "2027-01-02",
                "end_date": "2027-01-03",
            },
            "budget_estimate": {
                "transport": 20,
                "accommodation": 30,
                "activities": 5,
                "food_estimate": 10,
                "currency": "USD",
            },
        }
    )
    assert result.days[0].activity == "Walk"
    assert [e.action for e in events[:-1]] == [role for role, _ in ROLES]


def test_group_pricing_is_currency_independent():
    from datetime import date

    from app.schemas.trip import TransportMode, TravelStyle
    from app.tools.stay_activity_tools import recommend_stays_and_activities
    from app.tools.transport_tools import estimate_transport

    for code, rate in (("USD", 1), ("INR", 80)):
        stay = recommend_stays_and_activities(
            "Jaipur, India",
            TravelStyle.cultural,
            date(2027, 1, 1),
            3,
            travelers=3,
            currency=code,
            live_forex_rate=rate,
        )
        route = estimate_transport(
            "Delhi, India",
            "Jaipur, India",
            TransportMode.train,
            travelers=3,
            currency=code,
            live_forex_rate=rate,
        )
        assert stay.total_accommodation_cost == stay.cost_per_night * 3 * 2
        assert stay.total_food_cost == stay.daily_food_cost * 3 * 3
        assert route.total_cost == sum(leg.cost_estimate for leg in route.legs)
        amounts = [
            v / rate
            for v in (
                stay.total_accommodation_cost,
                stay.total_food_cost,
                route.total_cost,
            )
        ]
        if code == "USD":
            baseline = amounts
        else:
            assert amounts == baseline
