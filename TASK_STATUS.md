# TRIPPY verification

26 November 2026 · Rebuilt from the public main branch of Grim6135/Agentic_AI at `9706b87`. Changes are in this source package. The upstream repository has not been updated.

**Release status: awaiting live deployment.** No public frontend, backend or ADK URL was created. The Vercel CLI returned a DNS error reaching its API. This execution environment also denied outbound access to the package registries, Open-Meteo, Wikipedia, OSRM and the model providers, and denied a TCP loopback smoke test. Public account limits, bundle size, cold start, peak memory and live trip latency remain unmeasured.

## What ran

- All 73 backend tests passed in 66.51 seconds with 64 warnings. Backend verification uses FastAPI requests over ASGI, the actual A2A handler, in-process MCP protocol sessions, SQLite, ChromaDB, arithmetic checks and tests of the actual CrewAI and Google ADK runners with controlled model responses. A Windows pipe supplied the event-loop wakeup because this runner blocks local TCP sockets.
- The React application source passed a TypeScript 6.0.3 check using cached, lockfile-matched React types and local declarations for Vite assets. A server-side React render verified the planner form, submit control and date inputs. Four separate API-client checks passed for authenticated retrieval, validation errors, an HTML response and invalid JSON.
- The source contains 20 frontend test declarations. The exact Vitest/Vite dependencies were unavailable. The repository’s complete frontend test suite, TypeScript project build, production bundle, desktop/mobile browser flow and successful-trip screenshot remain pending.
- New Python modules passed compilation and undefined-name/import checks. Source scans found no provider-key signatures in application code. An offline npm production audit used cached information. A fresh dependency installation and advisory scan still require network access.

## Academic requirements

| # | Implemented | Verification boundary |
|---|---|---|
| 1 | Open-Meteo geocoding and date-specific forecasts, Wikipedia places, OSRM road routing | Provider contracts and failures tested. A live app request is pending. |
| 2 | Source, observation time, confidence and all four evidence statuses | Sources appear in results and owner-only traces. The SQLite catalog distinguishes checked references from estimates. |
| 3 | Official MCP client/server, five tools, per-trip audit and specialist allowlists | Protocol calls and forbidden-tool rejection exercised. |
| 4 | Group expenses, FX, room occupancy, contingency and independent decimal reconciliation | USD/INR, multiple travelers and an infeasible budget exercised. Booking and inventory prices remain unknown. |
| 5 | Five genuine sequential CrewAI tasks, scoped tools and task callbacks | Actual SDK orchestration exercised with a controlled model. Paid-provider execution pending. |
| 6 | Independently runnable ADK agent with an InMemoryRunner and a research tool | Actual ADK runner, model/tool exchange and callbacks exercised with a controlled model. |
| 7 | Bearer-protected A2A JSON-RPC, Agent Card and task artifact | HTTP requests tested in-process, including method rejection and correlation. Deployed cross-service networking pending. |
| 8 | Per-request Pydantic TripState, two refinements and unique task IDs | Concurrent INR/USD plans produced separate results and private traces. |
| 9 | Input bounds and screening, scoped tools, secret-safe errors, hourly limits, hashed per-trip bearer receipts | Controlled rejection, rate-limit and cross-trip access tests. No independent security assessment. |
| 10 | ADK/CrewAI callbacks, MCP timing, token metrics when supplied, optional Langfuse export | Local callbacks tested. Remote Langfuse delivery pending credentials and network access. |
| 11 | Interactive planner, budget, itinerary, provenance panels, trace events and refresh restoration | Backend and frontend source checks available. Browser acceptance remains pending. |

## Remaining action

Use a network-enabled build environment with the selected model credential, an authorized Vercel project, and a backend host with durable storage. Deploy both services, run one real trip locally and another through Vercel, then verify refresh, trace ownership and mobile rendering. No paid service was provisioned. Recipes for local startup, configuration and deployment are in [README.md](README.md) and [docs/deployment.md](docs/deployment.md).
