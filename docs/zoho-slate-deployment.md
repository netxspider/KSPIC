# Deploy the frontend with Zoho Catalyst Slate

Use Zoho Catalyst Slate for this Next.js frontend. Do not use basic static hosting: this application needs a Node.js Next.js runtime for the local API rewrite, or a public API base URL configured at build time.

## 1. Deploy the API and vector service first

The frontend is not a standalone demo. It calls the Python API for every KPI, FIR search, timeline, graph, map filter, and copilot response.

Deploy `Dockerfile.backend` to a private backend host with HTTPS. AWS App Runner is a natural fit because the application already calls Amazon Bedrock, but any container host is acceptable. Configure these server-only environment variables in the backend host:

    HOST=0.0.0.0
    PORT=8000
    AWS_BEARER_TOKEN_BEDROCK=<secret stored by the host>
    AWS_REGION=us-east-1
    QDRANT_URL=https://<private-or-cloud-qdrant-endpoint>
    CORS_ALLOWED_ORIGINS=https://<your-slate-url>,https://<your-custom-domain>

Never set the Bedrock bearer token as a Zoho Slate or `NEXT_PUBLIC_` variable. It belongs only in the API host's secret store. Keep Qdrant private where possible. After the backend has network access to Qdrant and Bedrock, run `python -m backend.ingest_qdrant` once in that backend environment to create the `ksp_case_chunks_bedrock_v1` collection.

Verify the API before moving on:

    curl https://<api-domain>/api/health

## 2. Push this repository to GitHub

Zoho Slate can deploy from GitHub and can automatically rebuild after a push. Confirm that `.venv`, Node modules, `.next`, and every `.env` file remain ignored. Do not commit credentials.

## 3. Create a Catalyst Slate app

1. Open Zoho Catalyst Console and create or select a project.
2. Open **Slate**, then choose **Deploy from GitHub repository**.
3. Authorize GitHub and choose the `netxspider/KSPIC` repository and production branch.
4. Set the project root directory to `frontend`.
5. Select Next.js (or accept Slate's detected framework and runtime).
6. In the environment-variable panel, add the non-secret value below:

       NEXT_PUBLIC_API_BASE_URL=https://<api-domain>

7. Keep the detected install/build/start settings, or use:

       Install: npm ci
       Build: npm run build
       Start: npm run start

8. Enable Auto Deploy only after the first deployment passes. Click Deploy and inspect the build log.

`NEXT_PUBLIC_API_BASE_URL` is intentionally public because it is only the HTTPS address of the API. It replaces the local Next.js `/api` proxy when the browser runs from the Slate domain.

## 4. Promote safely

Test the generated Slate preview URL first. Add that exact preview URL temporarily to `CORS_ALLOWED_ORIGINS`, then test:

- KPI cards load 5,000 FIRs.
- The Udupi burglary count is 56 and says that it is database-derived.
- Timeline, relationship graph, map filters, Show all, and voice transcription work.
- The copilot shows the vector retrieval status but never exposes a bearer token.

After review, promote the Slate deployment to production, add the production URL to `CORS_ALLOWED_ORIGINS`, then map the custom domain in Slate. Remove unused preview domains from the CORS allow-list.

## 5. Operational controls

- Rotate the bearer token that was exposed during development and store its replacement only in the backend host's secret manager.
- Restrict the API to HTTPS, an exact CORS allow-list, authenticated officers, and a private Qdrant endpoint before using non-synthetic data.
- Keep the SQLite database read-only in the container. Move to managed PostgreSQL and private object storage before operational use.
- Rebuild the Qdrant collection whenever source data changes, and log model IDs, retrieval IDs, citations, and user identity.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Slate page loads but KPIs are empty | Confirm `NEXT_PUBLIC_API_BASE_URL` was present during the build and points to an HTTPS API. |
| Browser reports a CORS error | Add the exact Slate origin, without a trailing slash, to `CORS_ALLOWED_ORIGINS`, then redeploy or restart the API. |
| API returns vector unavailable | Confirm the backend has `qdrant-client`, a reachable `QDRANT_URL`, Bedrock credentials, and the indexed collection. |
| Build renders unstyled HTML | Rebuild from the `frontend` root, confirm `frontend/app/globals.css` is in Git, then clear the browser cache. |
