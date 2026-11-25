# TRIPPY verification

The rebuild is based on Grim6135/Agentic_AI at commit `9706b87`. The verification below ran against this release on 26 November 2026 (India).

## Checks completed

- Python 3.12 on Linux: all 73 backend tests passed. These exercise FastAPI, A2A, MCP, SQLite, ChromaDB, CrewAI and Google ADK with controlled model responses. The test run reported SDK warnings.
- Node 24: all 20 frontend tests passed. The production TypeScript and Vite build succeeded. Lint reported zero warnings and zero errors. The npm dependency audit reported zero known vulnerabilities after updating the locked development dependency undici.
- Chromium opened the planner at 390 px and 1365 px. Both layouts fit within the viewport. The built frontend reached the API over HTTP, backend readiness passed, and the research service returned its agent card.
- The Groq credential authenticated against the account model catalog. The previous default model was unavailable. The release uses `groq/openai/gpt-oss-120b` for both agents.

The live Paris-to-Lyon request returned HTTP 503. The last attempt timed out connecting to Open-Meteo before model generation. A separate HTTPS check against the same geocoding host also timed out. No successful live itinerary, trace or refresh was verified. The application returns a retryable error for this case.

## Academic requirements

| # | Implemented | Verification boundary |
|---|---|---|
| 1 | Open-Meteo geocoding and date-specific forecasts, Wikipedia places, OSRM road routing | Provider contracts and failures tested. A live app request is pending. |
| 2 | Source, observation time, confidence and all four evidence statuses | Sources appear in results and owner-only traces. The SQLite catalog distinguishes checked references from estimates. |
| 3 | Official MCP client/server, five tools, per-trip audit and specialist allowlists | Protocol calls and forbidden-tool rejection exercised. |
| 4 | Group expenses, FX, room occupancy, contingency and independent decimal reconciliation | USD/INR, multiple travelers and an infeasible budget exercised. Booking and inventory prices remain unknown. |
| 5 | Five genuine sequential CrewAI tasks, scoped tools and task callbacks | Actual SDK orchestration exercised with a controlled model. Paid-provider execution pending. |
| 6 | Independently runnable ADK agent with an InMemoryRunner and a research tool | Actual ADK runner, model/tool exchange and callbacks exercised with a controlled model. |
| 7 | Bearer-protected A2A JSON-RPC, Agent Card and task artifact | HTTP requests tested in-process, including method rejection and correlation. Private HTTP connectivity verified in GitHub Codespaces. |
| 8 | Per-request Pydantic TripState, two refinements and unique task IDs | Concurrent INR/USD plans produced separate results and private traces. |
| 9 | Input bounds and screening, scoped tools, secret-safe errors, hourly limits, hashed per-trip bearer receipts | Controlled rejection, rate-limit and cross-trip access tests. No independent security assessment. |
| 10 | ADK/CrewAI callbacks, MCP timing, token metrics when supplied, optional Langfuse export | Local callbacks tested. Remote Langfuse delivery pending credentials and network access. |
| 11 | Interactive planner, budget, itinerary, provenance panels, trace events and refresh restoration | Backend and frontend source checks available. The planner form opened at desktop and mobile widths in Chromium. |

## Deployment

Production requires a persistent backend volume and a Vercel frontend configured with its API URL. See [deployment instructions](docs/deployment.md). The tests above ran in a temporary GitHub Codespace. Public production verification is pending.
