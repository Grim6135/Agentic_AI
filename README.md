# ✈️ TRIPPY — Autonomous AI Travel Planner (V4)

> An autonomous multi-agent travel planning platform powered by five specialist agents that collaborate to research destinations, compare transport options, curate accommodations and activities, calculate deterministic budgets with auto-refinement, and generate polished itineraries with verified citations.

---

## 🌟 Key Features

- **Five CrewAI Specialist Agents**:
  - 🗺️ **Destination Agent**: Ranks destinations based on user duration, style, interests, and budget ceiling.
  - 🚆 **Transport Agent**: Calculates transit times, routing distances, and realistic round-trip costs across flight, rail, and road.
  - 🏨 **Stay & Activity Agent**: Selects lodging categories, schedules daily highlights, and sets dining allowances.
  - 💰 **Budget Agent**: Deterministically verifies itemized costs against user maximums and runs a 2-pass reduction loop.
  - 📅 **Itinerary Agent**: Synthesizes validated estimates into structured, day-by-day itineraries with travel warnings.
- **RAG Knowledge Retrieval**: ChromaDB vector store loaded with curated destination guidebooks containing author authority, tags, and citation dates.
- **Resilient External Integrations**: Open-Meteo live weather forecasts and OSRM highway/geodesic flight routing with automatic fallback to offline climatology and regional distance matrices.
- **Deterministic Budget Math**: All financial additions, subtotals, and 8% contingency buffers are computed directly in Python to eliminate generative math errors.
- **Trip Persistence**: Thread-safe in-memory cache and atomic `.data/trips.json` serialization with read-only fallback resilience.
- **Production Observability**: Liveness (`GET /health`) and deep readiness (`GET /health/ready`) probes verifying vector store, storage permissions, and provider health.
- **Modern, Accessible UI**: React 18, TypeScript, Tailwind CSS v4, modal accessibility (`role="dialog"`, keyboard Escape dismiss), and one-click Trip ID copying.

---

## 🏛️ System Architecture

```
User Input ──► FastAPI Gateway ──► TrippyCrew Orchestrator
                                         │
        ┌────────────────────────────────┴────────────────────────────────┐
        ▼                                ▼                                ▼
  Destination Agent               Transport Agent                Stay & Activity Agent
  (RAG Guidebooks in Chroma)      (OSRM Route / Geodesic)        (Open-Meteo Weather)
        │                                │                                │
        └────────────────────────────────┬────────────────────────────────┘
                                         ▼
                             Deterministic Budget Math
                             (Itemized Sum + 8% Contingency)
                                         │
                     ┌───────────────────┴───────────────────┐
                     ▼                                       ▼
             [Within Budget]                         [Over Budget]
                     │                                       │
                     │                               Budget Agent
                     │                        (Up to 2 Refinement Passes)
                     │                                       │
                     └───────────────────┬───────────────────┘
                                         ▼
                                  Itinerary Agent
                                         │
                                         ▼
                            Storage & Persistence (.data)
                                         │
                                         ▼
                              Polished UI Itinerary
```

Detailed technical specifications are available in [`docs/architecture.md`](docs/architecture.md).

---

## 🚀 Quick Start & Installation

### Prerequisites

- **Python** ≥ 3.12 (Tested on Python 3.12, 3.13, 3.14)
- **Node.js** ≥ 20 with `npm`

### 1. Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate       # Linux / macOS
# .venv\Scripts\activate        # Windows PowerShell

# Install dependencies
pip install -r requirements.txt

# Create local environment file
cp .env.example .env

# Run development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend will be available at: `http://localhost:8000` (API documentation at `http://localhost:8000/docs`).

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Create local environment file
cp .env.example .env.local

# Run development server
npm run dev
```

Frontend will be available at: `http://localhost:5173`.

---

## ⚙️ Environment Variables Reference

### Backend (`backend/.env`)

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `APP_NAME` | string | `TRIPPY` | Name of the service application. |
| `ENVIRONMENT` | string | `development` | Runtime environment (`development`, `staging`, `production`). |
| `PORT` | integer | `8000` | HTTP listening port for Uvicorn. |
| `CORS_ORIGINS` | string / list | `["*"]` | Allowed CORS origins. Comma-separated in env or JSON array. |
| `STORAGE_DIR` | string | `.data` | Directory for persisted trip JSON files. |
| `LLM_PROVIDER` | string | `gemini` | Configured AI provider (`gemini` or `openai`). |
| `GEMINI_API_KEY` | string | `""` | Google AI Studio Gemini API key (optional for mock mode). |
| `OPENAI_API_KEY` | string | `""` | OpenAI platform API key (optional for mock mode). |
| `CHROMA_PERSIST_DIR` | string | `.chroma` | Directory for ChromaDB vector embeddings. |
| `WEATHER_PROVIDER` | string | `openmeteo` | Weather provider (`openmeteo`, `mock`, or `climatology`). |
| `ROUTE_PROVIDER` | string | `osrm` | Route distance provider (`osrm`, `mock`, or `matrix`). |

> **Security Note:** Sensitive keys are never transmitted to the frontend and are masked in backend diagnostics via `masked_secrets()`.

### Frontend (`frontend/.env.local`)

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `VITE_API_URL` | string | `http://localhost:8000` | Backend API root URL for client requests. |

---

## 🧪 Testing & Verification

TRIPPY includes a comprehensive test suite with **81 automated test cases** (100% pass rate).

### Run Backend Tests (62 Tests)
```bash
cd backend
source .venv/bin/activate
pytest tests -v
```

### Run Frontend Tests (19 Tests)
```bash
cd frontend
npm test
```

### Production Build Verification
```bash
cd frontend
npm run build
```

See [`docs/test-report.md`](docs/test-report.md) for detailed test breakdowns and the distinction between verified components and simulated live integrations.

---

## 🌐 API Endpoints Reference

| Method | Path | Summary | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | API Root | Returns service identity, version, and documentation links. |
| `GET` | `/health` | Liveness Probe | Immediate HTTP 200 health check for container orchestrators. |
| `GET` | `/health/ready` | Readiness Probe | Deep check of vector store, weather, routing, and storage disk permissions. |
| `POST` | `/api/trips/plan` | Plan Trip | Submits user preferences to the 5-agent pipeline; saves and returns itinerary. |
| `GET` | `/api/trips/{trip_id}` | Get Trip | Retrieves a previously planned trip by ID from persistent storage. |
| `GET` | `/api/trips` | List Trips | Lists up to 50 recently planned trips. |
| `GET` | `/docs` | Swagger UI | Interactive OpenAPI schema explorer. |

---

## 🚢 Production Deployment

Complete, step-by-step instructions for deploying TRIPPY to **Vercel** (Static Frontend) and **Render** (FastAPI Web Service) are documented in [`docs/deployment.md`](docs/deployment.md):

- **Render Configuration**: [`render.yaml`](render.yaml) & [`backend/render.yaml`](backend/render.yaml)
- **Vercel Configuration**: [`frontend/vercel.json`](frontend/vercel.json)

---

## ⚠️ Known Limitations & Honest Trade-offs

1. **Local Vector Embeddings**: In restricted offline environments, Chroma uses a deterministic 128-dimensional L2-normalized semantic embedding function to prevent downloading unauthenticated ONNX models from external sources.
2. **Persistence Storage**: Persistent trip storage is implemented with atomic JSON files in `.data/trips.json`. For multi-instance clustered enterprise workloads, migration to a hosted PostgreSQL/Supabase instance is recommended.
3. **Refinement Iteration Limit**: The budget refinement loop caps at 2 cycles to guarantee rapid response times and avoid infinite execution when requested budgets are mathematically unfeasible.
4. **Third-Party APIs**: External weather and route integrations rely on free open endpoints (Open-Meteo, OSRM). When network requests fail, the application gracefully provides seasonal climatology and great-circle geodesic calculations with explicit `is_live=False` tags.

---

## 🔄 Rollback Instructions

If a production deployment encounters issues:
1. **Frontend**: In the Vercel dashboard, navigate to **Deployments**, locate the last verified stable build, and click **Promote to Production**.
2. **Backend**: In the Render dashboard, navigate to the web service, open the **Events / Deploys** tab, and select **Rollback to this deploy**.
3. **Local**: To revert local code changes:
   ```bash
   git checkout master
   git clean -fd
   ```

---

## 📚 Presentation & Documentation Links

- [How TRIPPY Works: Complete Walkthrough](docs/how-trippy-works.md)
- [System Architecture Specification](docs/architecture.md)
- [Teacher Presentation Script (5–7 min)](docs/demo-script.md)
- [Comprehensive Test Report](docs/test-report.md)
- [Deployment & Operations Runbook](docs/deployment.md)

---

## 📄 License

Educational demonstration project. Built for academic evaluation.
