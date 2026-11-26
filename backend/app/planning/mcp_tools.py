import json
from datetime import date
from time import monotonic

try:
    from mcp.server.fastmcp import FastMCP
    from mcp.shared.memory import create_connected_server_and_client_session
except (ImportError, ModuleNotFoundError):
    FastMCP = None
    create_connected_server_and_client_session = None

from app.integrations import places_service, route_service, weather_service
from app.tools.budget_tools import calculate_itemized_budget

from .models import Event, clean
from .registry import lookup

if FastMCP:
    server = FastMCP("TRIPPY")
else:
    class _FallbackMCP:
        def tool(self):
            return lambda fn: fn
    server = _FallbackMCP()
TOOLS = frozenset(
    {
        "search_destination_info",
        "lookup_travel_records",
        "calculate_trip_budget",
        "get_weather",
        "get_route",
    }
)


@server.tool()
async def search_destination_info(destination: str) -> dict:
    """Find a Wikipedia summary and nearby places."""
    info = await places_service.get_destination_info(destination)
    if not info:
        return {}
    return {
        "title": clean(info.title),
        "summary": clean(info.summary),
        "places": [
            {"name": clean(p.name, 100), "source": p.source_url}
            for p in info.landmarks[:12]
        ],
    }


@server.tool()
def lookup_travel_records(destination: str) -> dict:
    """Look up the local travel guide registry."""
    return lookup(destination)


@server.tool()
def calculate_trip_budget(
    transport: float, lodging: float, activities: float, food: float, currency: str
) -> dict:
    """Calculate group totals including an eight percent contingency."""
    return calculate_itemized_budget(
        transport, lodging, activities, food, currency=currency
    ).model_dump()


@server.tool()
async def get_weather(destination: str, start: str, end: str) -> dict:
    """Retrieve weather for the requested dates or a labeled estimate."""
    try:
        value = await weather_service.get_forecast(
            destination, date.fromisoformat(start), date.fromisoformat(end)
        )
    except (RuntimeError, OSError):
        return {}
    return value.model_dump(mode="json") if value else {}


@server.tool()
async def get_route(origin: str, destination: str, mode: str) -> dict:
    """Retrieve a road route or a labeled flight distance estimate."""
    try:
        value = await route_service.get_route(origin, destination, mode)
    except (RuntimeError, OSError):
        return {}
    return value.model_dump(mode="json") if value else {}


async def call(session, state, name, **args):
    if name not in TOOLS:
        raise PermissionError("Tool access denied")
    started = monotonic()
    result = await session.call_tool(name, args)
    if result.isError:
        raise RuntimeError("Travel tool failed")
    state.events.append(
        Event(
            component="MCP", action=name, elapsed_ms=int((monotonic() - started) * 1000)
        )
    )
    return json.loads(result.content[0].text)


def connect():
    if create_connected_server_and_client_session and hasattr(server, "_mcp_server"):
        return create_connected_server_and_client_session(server._mcp_server)

    import inspect
    from contextlib import asynccontextmanager
    from types import SimpleNamespace

    _TOOL_FUNCS = {
        "search_destination_info": search_destination_info,
        "lookup_travel_records": lookup_travel_records,
        "calculate_trip_budget": calculate_trip_budget,
        "get_weather": get_weather,
        "get_route": get_route,
    }

    class _LocalSession:
        async def call_tool(self, name, args):
            fn = _TOOL_FUNCS[name]
            if inspect.iscoroutinefunction(fn):
                res = await fn(**args)
            else:
                res = fn(**args)
            return SimpleNamespace(isError=False, content=[SimpleNamespace(text=json.dumps(res, ensure_ascii=False))])

    @asynccontextmanager
    async def _direct_session():
        yield _LocalSession()

    return _direct_session()


if __name__ == "__main__":
    server.run(transport="stdio")
