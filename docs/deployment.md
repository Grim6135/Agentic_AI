# TRIPPY — Production Deployment & Rollback Guide

This guide describes how to deploy the TRIPPY travel planning application to production using **Vercel** for the static frontend and **Render** (or Railway/Fly.io/Docker) for the FastAPI backend service.

---

## Architecture Overview

```
                                      +---------------------------------------------+
                                      |                 USER BROWSER                |
                                      +---------------------------------------------+
                                                             |
                                            HTTPS (Static Assets & React App)
                                                             v
                                      +---------------------------------------------+
                                      |           VERCEL STATIC HOSTING             |
                                      |   - Vite React Single Page App              |
                                      |   - vercel.json SPA rewrites               |
                                      |   - VITE_API_BASE_URL points to Render API  |
                                      +---------------------------------------------+
                                                             |
                                            HTTPS API Requests (/api/trips/plan)
                                                             v
                                      +---------------------------------------------+
                                      |            RENDER WEB SERVICE               |
                                      |   - FastAPI Backend (Uvicorn ASGI)          |
                                      |   - 5 CrewAI Specialist Agents              |
                                      |   - ChromaDB RAG Vector Store               |
                                      |   - Trip Persistence Store (in-memory/disk) |
                                      |   - Open-Meteo & OSRM Live Integrations     |
                                      |   - Health Readiness Check (/health/ready)  |
                                      +---------------------------------------------+
```

---

## 1. Backend Deployment (Render)

### Option A: One-Click Blueprint (`render.yaml`)

TRIPPY includes a pre-configured `render.yaml` blueprint:
1. Connect your GitHub repository to [Render Dashboard](https://dashboard.render.com).
2. Click **New +** → **Blueprint**.
3. Select your repository. Render automatically reads `render.yaml` and provisions:
   - **Service Name**: `trippy-backend`
   - **Runtime**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path**: `/health/ready`
4. In Environment Settings, verify or customize:
   - `ENVIRONMENT`: `production`
   - `CORS_ORIGINS`: `https://<your-frontend>.vercel.app,http://localhost:5173`
   - `RAG_ENABLED`: `true`
   - `RAG_PERSIST_DIR`: `.chroma`
   - `STORAGE_DIR`: `.data`
   - `WEATHER_PROVIDER`: `open-meteo`
   - `MAPS_PROVIDER`: `osrm`
   - `INTEGRATION_TIMEOUT_SECONDS`: `5.0`
5. Click **Apply**. Once built, note your backend URL (e.g. `https://trippy-backend-xyz.onrender.com`).

### Option B: Manual Setup via Render Web UI

1. Click **New +** → **Web Service**.
2. Set **Root Directory** to `backend`.
3. Set **Runtime** to `Python 3`.
4. Set **Build Command**: `pip install -r requirements.txt`.
5. Set **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
6. Under **Advanced** → **Health Check Path**, enter `/health/ready`.
7. Under **Environment Variables**, add:
   - `ENVIRONMENT` = `production`
   - `CORS_ORIGINS` = `https://<your-frontend>.vercel.app,http://localhost:5173`
   - `RAG_ENABLED` = `true`
   - `STORAGE_DIR` = `.data`
   - `WEATHER_PROVIDER` = `open-meteo`
   - `MAPS_PROVIDER` = `osrm`

---

## 2. Frontend Deployment (Vercel)

### Step 1: Connect Repository to Vercel

1. Log into [Vercel Dashboard](https://vercel.com/dashboard) and click **Add New...** → **Project**.
2. Import your TRIPPY Git repository.

### Step 2: Configure Build Settings

- **Framework Preset**: `Vite`
- **Root Directory**: `frontend`
- **Build Command**: `npm run build` (runs `tsc -b && vite build`)
- **Output Directory**: `dist`
- **Install Command**: `npm install`

### Step 3: Configure Environment Variables

Under **Environment Variables**, add:
- `VITE_API_BASE_URL` = `https://<your-backend-app>.onrender.com/api`

> [!IMPORTANT]
> Always point `VITE_API_BASE_URL` to the public HTTPS URL of your deployed backend followed by `/api`. Never leave it as `http://localhost:8000` or `/api` on static hosting unless reverse proxy rewrites are configured in `vercel.json`.

### Step 4: Deploy

Click **Deploy**. Vercel will build the React bundle and deploy it with `frontend/vercel.json` SPA rewrite rules.

---

## 3. Verifying the Deployment

Run these validation commands against your deployed endpoints:

### 1. Basic Liveness Check
```bash
curl -i https://<your-backend-app>.onrender.com/health
```
**Expected Response**:
```json
HTTP/1.1 200 OK
{"status":"ok","version":"0.1.0"}
```

### 2. Deep Readiness Check
```bash
curl -i https://<your-backend-app>.onrender.com/health/ready
```
**Expected Response**:
```json
HTTP/1.1 200 OK
{
  "status": "ready",
  "version": "0.1.0",
  "environment": "production",
  "rag_enabled": true,
  "rag_documents_loaded": 4,
  "weather_provider": "open-meteo",
  "maps_provider": "osrm",
  "storage_writable": true,
  "stored_trips_count": 0
}
```

### 3. End-to-End Planning Flow Check
```bash
curl -i -X POST https://<your-backend-app>.onrender.com/api/trips/plan \
  -H "Content-Type: application/json" \
  -d '{
    "origin": "New York, USA",
    "destinations": ["Kyoto, Japan"],
    "start_date": "2026-11-15",
    "end_date": "2026-11-20",
    "budget_max": 2500,
    "travelers": 2,
    "travel_style": "cultural",
    "preferred_transport": "flight"
  }'
```
**Expected Response**:
- HTTP 200 with complete `TripResult` containing `trip_id`, `weather` (`is_live: true`), `route_estimate` (`is_live: true`), `rag_sources`, and `budget`.

### 4. Trip Persistence Retrieval Check
```bash
curl -i https://<your-backend-app>.onrender.com/api/trips/<trip_id>
```
**Expected Response**:
- HTTP 200 returning the persisted trip.

---

## 4. Rollback Runbook

### A. Vercel Instant Frontend Rollback

Vercel maintains immutable deployments for every build:
1. **Via Web Dashboard**:
   - Navigate to your project on Vercel Dashboard.
   - Go to the **Deployments** tab.
   - Locate the previous known-good deployment.
   - Click the three dots (`...`) menu and select **Promote to Production** (or **Rollback to this deployment**).
   - Traffic instantly switches in <100ms.
2. **Via Vercel CLI**:
   ```bash
   vercel rollback <deployment-url-or-id>
   ```

### B. Render Backend Rollback

1. **Via Render Web Dashboard**:
   - Open your `trippy-backend` service on Render.
   - Go to the **Events** or **Deploys** tab.
   - Find the last stable deployment before the incident.
   - Click **Rollback to this deploy**.
2. **Via Git Revert**:
   ```bash
   git revert HEAD
   git push origin main
   ```
   Render will automatically trigger a new deployment from the reverted commit.

---

## 5. Demonstrability & Free Tier Operational Notes

1. **Zero Paid Credentials**:
   - TRIPPY runs 100% out-of-the-box in deterministic autonomous mode.
   - Document ingestion uses curated Markdown guides in `backend/app/rag/data/` with local n-gram semantic vector embeddings.
   - Weather uses Open-Meteo's public API (no key required).
   - Routing uses OSRM's public routing engine and Haversine Geodesic calculation.
   - If external APIs are blocked or timeout, fallback climatology and distance matrices engage transparently with honest `is_live=False` indicators.

2. **Render Free Tier Cold Starts**:
   - Free instances spin down after 15 minutes of inactivity.
   - The initial request after a spin-down may take ~30–50 seconds to boot.
   - The frontend API client includes safe timeouts and user-friendly error banners with retry buttons.

3. **Remaining Risks & Mitigations**:
   - **Ephemeral Filesystem on Free Dynos**: In free-tier serverless containers, local disk storage resets on restart. To mitigate this in high-traffic production, set `DATABASE_URL` in `.env` to connect PostgreSQL or Supabase.
   - **CORS Misconfiguration**: Ensure `CORS_ORIGINS` in Render matches your exact Vercel frontend domain (including protocol `https://` without a trailing slash).
