# Deployment

The prepared layout serves React on Vercel and both Python services on a single persistent container host. Only the FastAPI port needs an HTTPS ingress. ADK runs privately on loopback. The API worker is terminated on timeout. Planning stays inside the active request. Allow at least 250 seconds on the backend ingress.

## Hosting requirements

Vercel Services can route multiple runtimes under one project. Vercel Functions expose temporary writable storage. Durable trip receipts, traces and hourly quotas in this build require a persistent SQLite volume. Built-in guide documents rebuild the Chroma index at startup. The official MCP client uses in-process protocol streams. An all-Vercel configuration would require an external durable store plus measured package size, memory, runtime and cold-start behavior. Those measurements require an actual account deployment.

[Vercel Services](https://vercel.com/docs/services) · [Runtime filesystem](https://vercel.com/docs/functions/runtimes) · [Function limits](https://vercel.com/docs/functions/limitations)

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
