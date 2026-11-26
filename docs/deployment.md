# Deployment

## Vercel Services

Import this GitHub repository on the main branch with project root `./` and the Services preset. Vercel builds the Vite frontend and two Python containers. The browser calls `/api` on the same domain. Only the backend receives the internal research service URL through the `RESEARCH_SERVICE_URL` binding. Vercel sets this value automatically.

Connect a PostgreSQL database such as Neon through Vercel Storage. Make its pooled `DATABASE_URL` available to the backend. The first request initializes the tables. The database stores trips, hashed owner receipts, traces and hourly quotas across instances. Keep production and preview data separate.

Set `GROQ_API_KEY` and a random shared `ADK_SERVICE_TOKEN` as server-side environment variables for the backend and research services. Leave `VITE_API_BASE_URL` unset for a same-origin deployment. Choose Node 24 for the frontend. After deployment, check `/api/health/ready` and submit a trip through the form. For local service routing, run `vercel dev` from the project root with Docker running.

## Existing container host

Build from the backend directory. Set `ENVIRONMENT=production`, `STORAGE_DIR=/var/lib/trippy`, an exact `CORS_ORIGINS` JSON list containing the frontend HTTPS origin, the model credentials, and `ADK_SERVICE_TOKEN` in a server-only environment file. The main API and ADK share that token. The default ADK URL is `http://127.0.0.1:8001`. For a separated host, use private networking or HTTPS and set `ADK_BASE_URL` on both services.

```sh
docker build -t trippy-backend ./backend
docker volume create trippy-data
docker run -d --name trippy-backend --restart unless-stopped --env-file ./backend/.env -e ENVIRONMENT=production -e STORAGE_DIR=/var/lib/trippy -v trippy-data:/var/lib/trippy -p 127.0.0.1:8000:8000 trippy-backend
```

Route the existing host's HTTPS reverse proxy to port 8000. Keep a single host using the volume. Use a shared database before scaling to multiple hosts. The optional Render blueprints specify a billed instance and a persistent disk. Review the estimate and authorize the service before applying either blueprint.

## Vercel frontend

Use the `frontend` project root, Vite preset, Node.js 24, `npm ci`, `npm run build` and output directory `dist`. Set only `VITE_API_BASE_URL=https://<your-backend-host>/api` for this app in Vercel. Configure the actual Vercel origin in backend CORS and rebuild the frontend when the API URL changes. From `frontend`, an authenticated Vercel CLI can link the authorized project with `vercel link` and publish it using `vercel --prod`.

## Verification and cost

Check backend `/health/ready`. Submit a real trip through the frontend, open Sources and Agent execution, refresh in the same tab and verify the itinerary returns. A different tab without the receipt should receive 401 from the private trace endpoint. Test the form on a narrow viewport. Record the actual successful trip time and a screenshot only after this passes.

The example Render configuration specifies one Standard instance and a 1 GB disk. At the published rates the illustrative base is USD 25.25 per month before usage, model calls and applicable taxes. Capacity for this workload still needs measurement. Existing infrastructure may have a different incremental cost. No resources were provisioned during the rebuild.

[Render pricing](https://render.com/pricing)
