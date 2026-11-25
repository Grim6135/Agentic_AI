# TRIPPY V4 — System Architecture & Design Specification

## 1. Executive Summary

**TRIPPY** is a production-grade, autonomous multi-agent travel planning platform. It bridges high-level user travel aspirations with deterministic scheduling, itemized budgeting, and curated knowledge retrieval. 

The system leverages a decoupled modern stack:
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS v4.
- **Backend API**: Python 3.12+, FastAPI, Pydantic v2.
- **Agentic Orchestration**: Five CrewAI-pattern specialist agents coordinated through `TrippyCrew`.
- **RAG Engine**: ChromaDB with document frontmatter parsing, semantic chunking, and source citation traceability.
- **Integration Layer**: Resilient weather (Open-Meteo / Climatology) and routing (OSRM / Geodesic) services with live verification indicators.
- **Persistence**: Thread-safe in-memory caching with atomic disk serialization and read-only resilience.

---

## 2. End-to-End System Architecture

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 PRESENTATION LAYER                                      │
│                                                                                        │
│   React 18 + Vite SPA  ◄──────────────────────────────────►  Tailwind CSS v4 Design    │
│   • TripPreferencesForm with Date Validation & Presets                                 │
│   • Itinerary View with Live Badges, Source Badges & Cost Breakdown                    │
│   • Trip Persistence & One-Click ID Copying                                            │
│   • Resilient Error Toasts & Graceful Degradation Banners                              │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ HTTPS / JSON REST
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 FASTAPI APPLICATION GATEWAY                             │
│                                                                                        │
│  Routers:                                                                              │
│  ├── /health           -> Liveness probe (Immediate 200 OK)                            │
│  ├── /health/ready     -> Deep readiness probe (RAG, Providers, Persistence Storage)   │
│  └── /api/trips/*      -> POST /plan, GET /{trip_id}, GET / (List)                     │
│                                                                                        │
│  Middleware & Security:                                                                │
│  • CORS with Dynamic Origin Validator (spec-compliant wildcard credential handling)   │
│  • Secret Masking on startup diagnostics (`masked_secrets()`)                          │
│  • Strict Pydantic v2 Request Validation (`TripPreferences`)                           │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              TRIPPYCREW MULTI-AGENT ENGINE                             │
│                                                                                        │
│  ┌───────────────────────┐      ┌─────────────────────────┐      ┌──────────────────┐  │
│  │ 1. Destination Agent  │ ───► │ 2. Transport Specialist │ ───► │ 3. Stay/Activity │  │
│  │ RAG Matchmaking &     │      │ Routing, Mode, Time &   │      │ Lodging, Dining, │  │
│  │ Affinity Scoring      │      │ Transit Cost Bounds     │      │ & Curated Sights │  │
│  └───────────────────────┘      └─────────────────────────┘      └──────────────────┘  │
│                                              │                                         │
│                                              ▼                                         │
│                                 ┌─────────────────────────┐                            │
│                                 │ Deterministic Python    │                            │
│                                 │ Budget Math Computation │                            │
│                                 └────────────┬────────────┘                            │
│                                              │                                         │
│              ┌───────────────────────────────┴───────────────────────────────┐         │
│              │ (Total Cost vs User Budget Max)                               │         │
│              ▼                                                               ▼         │
│     [Over Budget: Refinement Loop]                                  [Within Budget]    │
│     • Up to 2 Iterative Passes                                               │         │
│     • Downgrade Transit / Lodging / Activities                               │         │
│     • Recalculate Deterministically                                          │         │
│              │                                                               │         │
│              └───────────────────────────────┬───────────────────────────────┘         │
│                                              ▼                                         │
│                                 ┌─────────────────────────┐                            │
│                                 │ 5. Itinerary Agent      │                            │
│                                 │ Day-by-day sequencing,  │                            │
│                                 │ practical tips, notices │                            │
│                                 └────────────┬────────────┘                            │
└──────────────────────────────────────────────┼─────────────────────────────────────────┘
                                               │
                      ┌────────────────────────┼────────────────────────┐
                      ▼                        ▼                        ▼
       ┌────────────────────────┐  ┌───────────────────────┐  ┌──────────────────────┐
       │   RAG KNOWLEDGE BASE   │  │ EXTERNAL INTEGRATIONS │  │  PERSISTENCE STORE   │
       │                        │  │                       │  │                      │
       │ • ChromaDB Collection  │  │ • Open-Meteo Weather  │  │ • Thread-Safe Cache  │
       │ • Markdown Guidebooks  │  │ • OSRM Highway Engine │  │ • Atomic Disk Write  │
       │ • YAML Frontmatter     │  │ • Geodesic Great-     │  │   (.data/trips.json) │
       │ • 128-d L2 Embeddings  │  │   Circle Calculator   │  │ • Read-Only Fallback │
       │ • Source Citations     │  │ • Climatology & Matrix│  │                      │
       │                        │  │   Offline Fallbacks   │  │                      │
       └────────────────────────┘  └───────────────────────┘  └──────────────────────┘
```

---

## 3. Specialist Agent Roles & Responsibilities

| Agent | Core Objective | Inputs | Tools Utilized | Output Schema |
| :--- | :--- | :--- | :--- | :--- |
| **1. Destination Agent** | Discovers and ranks target cities aligned with user duration, style, interests, and budget capacity. | `TripPreferences`, RAG knowledge passages. | `find_destinations_tool`, `query_destination_knowledge_tool` | `DestinationCandidate` (Name, country, suitability score, matching highlights, RAG citations) |
| **2. Transport Agent** | Calculates realistic transit routes, travel duration, and round-trip costs across air, rail, or road. | Origin, selected destination, traveler count, refinement tier. | `estimate_transport_tool`, `get_route_estimate_tool` | `TransportEstimate` (Primary mode, total transit time, itemized cost, departure/return notes) |
| **3. Stay & Activity Agent** | Curates neighborhood accommodations, signature excursions, and dining allocations. | Destination, duration, traveler count, interests, refinement tier. | `curate_stay_and_activities_tool`, `get_weather_forecast_tool` | `StayActivityEstimate` (Lodging tier, cost, selected attractions, daily food budget) |
| **4. Budget Agent** | Enforces mathematical cost constraints, audits itemized expenses, and plans tier downgrades. | Itemized costs, maximum user budget, refinement pass counter. | `calculate_budget_math_tool`, `refine_budget_tool` | `BudgetBreakdown` (Transport, lodging, activities, food, 8% contingency buffer, total, status) |
| **5. Itinerary Agent** | Formulates daily schedule narrative, optimizes transit flow, and provides actionable destination advice. | Validated candidate, transport, stay/activities, budget, weather forecast. | Internal narrative synthesizer & day-by-day scheduler | `TripResult` (Complete day-by-day itinerary, source citations, weather cards, route cards) |

---

## 4. Deterministic Budget Math & Refinement Loop

A core architectural principle of TRIPPY is that **budget calculations are never left to generative LLM hallucinations**. All financial math is evaluated deterministically in Python:

$$\text{Subtotal} = \text{Transport Cost} + \text{Lodging Cost} + \text{Activity Cost} + \text{Food Allowance}$$
$$\text{Contingency Buffer} = \text{Round}(\text{Subtotal} \times 0.08)$$
$$\text{Grand Total} = \text{Subtotal} + \text{Contingency Buffer}$$

### Refinement Workflow:
1. **Pass 0 (Initial Estimation)**: Standard mid-tier or preferred preferences.
2. **Evaluation**: If $\text{Grand Total} \le \text{budget\_max}$, budget validation passes immediately.
3. **Pass 1 (First Refinement)**: If over budget, the Budget Agent activates Refinement Tier 1:
   - Lodging downgraded from premium/boutique to verified comfortable standard hotel.
   - Transport shifted to saver/advance flight or standard train fares.
   - Activities rebalanced to mix free highlights with paid admissions.
   - Python recalculates itemized totals.
4. **Pass 2 (Second Refinement)**: If still over budget, Refinement Tier 2 is applied:
   - Lodging shifted to clean hostels, guesthouses, or budget rooms.
   - Transport set to economy coach/bus or regional public transit.
   - Activities focused on self-guided walking tours and free public sights.
   - Dining shifted to local markets and street food allowances.
5. **Hard Limit Safety**: A maximum of 2 refinement iterations is strictly enforced. If the requested trip remains mathematically unfeasible within the ceiling, the system returns the most optimized plan accompanied by a prominent financial advisory warning (`is_over_budget: true`).

---

## 5. RAG Pipeline (Retrieval-Augmented Generation)

```
Guidebook Markdown Files
(/backend/app/rag/knowledge_docs/*.md)
          │
          ▼
Frontmatter Parser (Title, Destination, Country, Tags, Authority, Last Verified)
          │
          ▼
Section-Aware Semantic Chunker (Headers, Bullet lists, 500-char overlap)
          │
          ▼
ChromaDB Collection ("destination_knowledge")
          │
          ▼
Query Formulation (Destination name + User Interests)
          │
          ▼
Cosine Distance Vector Retrieval (Top-k = 3)
          │
          ▼
Enriched Prompt Injection & Source Citations Output:
- Source Name: "Kyoto Cultural & Culinary Guide"
- Authority: "Kyoto Tourism Research Group"
- Last Verified: "2026-03"
```

### Zero-Crash RAG Guarantee:
- If ChromaDB is initializing or an index file is unavailable, the pipeline falls back gracefully to in-memory parsed documents.
- If a destination is not currently documented in the local vector store, the agent handles the query safely using general knowledge without throwing exceptions or blocking the user.

---

## 6. External Integrations Architecture

### Weather Integration (`backend/app/integrations/weather.py`)
- **Live Provider (`OpenMeteoWeatherProvider`)**: Queries Open-Meteo's open weather forecast APIs (WMO condition codes, high/low Celsius, precipitation probability).
- **Offline Climatology (`ClimatologyFallbackWeatherProvider`)**: Built-in seasonal temperature and weather models for major global destination hubs.
- **Mock Provider (`MockWeatherProvider`)**: Deterministic fixtures for unit testing without network dependencies.
- **Safety**: 5.0-second HTTP timeout with a 600-second in-memory TTL cache. Verified data is stamped `is_live=True`; fallback estimates are stamped `is_live=False`.

### Maps & Routing Integration (`backend/app/integrations/route.py`)
- **Live Provider (`OSRMRouteProvider`)**: Queries the Open Source Routing Machine (OSRM) overland routing engine for itineraries within 1,200 km.
- **Geodesic Calculator (`geodesic_great_circle_distance`)**: Computes spherical distance and estimated cruising flight durations for transcontinental journeys.
- **Offline Distance Matrix (`MatrixFallbackRouteProvider`)**: Reliable regional distance estimates when external APIs are unreachable.
- **Safety**: 5.0-second timeout with TTL caching. Verified routes are stamped `is_live=True`; geodesic or matrix calculations are stamped `is_live=False`.

---

## 7. Storage & Persistence Architecture

The persistence layer (`backend/app/storage/repository.py`) guarantees data safety:
1. **Thread-Safe In-Memory Cache**: Uses `threading.Lock` for fast read access and concurrent write safety.
2. **Atomic Disk Writes**: Writes JSON records to a temporary file (`.trips.json.tmp`) before performing an atomic filesystem rename to `.data/trips.json`.
3. **Read-Only / Ephemeral Filesystem Fallback**: If file write operations fail due to container permission limits or serverless environments, the repository transparently falls back to memory-only storage without throwing errors.
4. **REST Endpoints**:
   - `POST /api/trips/plan`: Plans and persists the trip, returning a unique `trip_id`.
   - `GET /api/trips/{trip_id}`: Retrieves stored trip with all itinerary details.
   - `GET /api/trips`: Lists the 50 most recent planned trips with summary metrics.

---

## 8. Health & Observability Model

- **Liveness Probe (`GET /health`)**: Returns immediate HTTP 200 `{ status: "healthy", version: "0.4.0" }`. Designed for Kubernetes/Render container liveness checks.
- **Deep Readiness Probe (`GET /health/ready`)**:
  - Checks ChromaDB vector store readiness.
  - Verifies weather provider configuration.
  - Verifies routing engine status.
  - Tests persistence storage directory write permissions.
  - Returns component-level status (`status: "ready"` or `"degraded"`).

---

## 9. Security & Secret Protection

- **Server-Side Key Isolation**: All LLM and API keys reside strictly on the backend. No keys are exposed to the browser.
- **Masked Diagnostics**: Startup health reports mask sensitive strings (e.g. `sk-pro...89ab`).
- **Strict Input Sanitization**: Pydantic v2 validates date formats, traveler limits ($1 \le n \le 20$), and positive budget constraints.
- **CORS Protection**: Enforces explicit allowed origins, safely handling credential requirements when wildcard origins are configured.
