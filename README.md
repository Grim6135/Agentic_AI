# TRIPPY

TRIPPY builds a travel plan with a Google ADK research agent, five CrewAI specialists and an audited MCP tool session. The public planning endpoint uses these frameworks. The original Python specialist classes remain available to existing callers.

## Run locally on Windows

Use Python 3.12 and Node.js 24.15 or newer on the 24.x line. From the project root, install the backend and create its settings file. The last command preserves an existing configuration.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
if (!(Test-Path .env)) { Copy-Item .env.example .env }
```

Set `GROQ_API_KEY` in `backend/.env` and give `ADK_SERVICE_TOKEN` a long random value. Both services load that file when started from `backend`. To generate the internal token locally without printing it, run this once for a fresh example file.

```powershell
.\.venv\Scripts\python -c "from pathlib import Path; import secrets; p=Path('.env'); s=p.read_text(); p.write_text(s.replace('ADK_SERVICE_TOKEN=\n', 'ADK_SERVICE_TOKEN='+secrets.token_urlsafe(32)+'\n'))"
```

The default ADK and CrewAI model is `groq/llama-3.3-70b-versatile`. To use OpenRouter, set `OPENROUTER_API_KEY` and choose a tool-capable model available to your account using `openrouter/<provider>/<model>` for `ADK_MODEL` and `CREW_MODEL`. The selected provider controls pricing and availability. Both services can also use Gemini. Use `gemini-<model suffix>` for ADK, `gemini/<model id>` for CrewAI and set `GOOGLE_API_KEY`. Open-Meteo, OSRM and Wikipedia require no key for this application.

Start each command in its own PowerShell window from the project root.

```powershell
cd backend
.\.venv\Scripts\python -m uvicorn app.adk_service.server:adk_app --host 127.0.0.1 --port 8001
```

```powershell
cd backend
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev -- --host 127.0.0.1 --port 5173
```

Open `http://127.0.0.1:5173`. API documentation is at `http://127.0.0.1:8000/docs`. The research card is at `http://127.0.0.1:8001/.well-known/agent.json`.

## How a request runs

1. FastAPI validates preferences, checks the hourly quota and geocodes the locations. The planner handles one selected destination per itinerary. When choices are supplied, it uses the first. Without a choice, ADK selects a destination.
2. The API sends a JSON-RPC `message/send` over authenticated HTTP to ADK. Its research agent calls a geocoding and Wikipedia tool. The response carries the trip correlation ID.
3. An official MCP client exchanges protocol messages with the server over in-process streams. Its five tools retrieve destination information, look up bundled documents in SQLite, retrieve weather and routes, and calculate the group budget. The server also supports stdio through `python -m app.planning.mcp_tools`.
4. Python estimates transport, lodging, activities and meals, applies an 8% contingency and reconciles the result independently using decimal arithmetic. Lodging assumes two travelers per room, rounded up. The planner allows two budget refinements. Prices and availability require separate booking confirmation.
5. A real sequential CrewAI crew creates the itinerary. Each specialist receives the approved trip evidence and role-specific tool permissions. The parent process enforces a worker deadline. Failure produces a retryable error.
6. SQLite stores the result and its audit trail. The API returns a per-trip bearer token. The UI retains the receipt for the browser tab and restores the result on refresh. The source and execution panels show provenance, MCP calls and agent callbacks.

## Configuration

The Vercel frontend uses only `VITE_API_BASE_URL`. The server reads `ADK_BASE_URL`, `ADK_SERVICE_TOKEN`, `ADK_MODEL`, `CREW_MODEL` and the key for each selected provider. Use `GROQ_API_KEY`, `OPENROUTER_API_KEY`, `GOOGLE_API_KEY`, or `AI_API_KEY` for an OpenAI CrewAI model. Configure `ENVIRONMENT`, `STORAGE_DIR`, `CORS_ORIGINS`, `HOURLY_CLIENT_LIMIT` and `HOURLY_GLOBAL_LIMIT` on the backend host. Optional Langfuse export reads `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` and `LANGFUSE_BASE_URL`. It sends execution metadata and available token counts. See `backend/.env.example` for defaults.

## API and tests

| Method | Endpoint | Access |
|---|---|---|
| POST | `/api/trips/plan` | Public, rate limited |
| GET | `/api/trips/{id}` and `/api/trips/{id}/trace` | Trip bearer token |
| GET | `/health`, `/health/ready`, `/docs` | API service |
| GET | `/.well-known/agent.json` and `/a2a/agent-card` | Research service |
| POST | `/a2a` and `/a2a/tasks` | Research service bearer token and JSON-RPC envelope |

From `backend`, run `.\.venv\Scripts\python -m pytest -q`. From `frontend`, run `npm.cmd test` and `npm.cmd run build`. The SDK integration tests substitute model responses so they can exercise the actual frameworks without provider charges. A public acceptance test additionally requires a real itinerary through the deployed UI.

[Deployment instructions](docs/deployment.md) · [Current verification results](TASK_STATUS.md)
