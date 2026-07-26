# KSP Intelligence Copilot

Evidence-grounded investigation assistant for Karnataka State Police - built as a working, local-first hackathon system rather than a chatbot mockup.

## What is real in this repository

- **5,000 relational FIR records** in `data/ksp_crime.db`, generated from the provided Police FIR ER diagram.
- The schema preserves the document's named core tables: `CaseMaster`, complainants, victims, accused, arrest/surrender, acts/sections, crime heads, status, courts, districts, units, ranks, designations, employees, chargesheets and lookup masters.
- Intelligence-layer extensions (`Evidence`, `CaseVehicle`, `CasePhone`, `WitnessStatement`) are deliberately separate from the FIR schema, enabling retrieval and graph traversal without pretending they are CCTNS source tables.
- **SQL search** uses parameterized, allow-listed filters - no model-written SQL is executed.
- **RAG retrieval** uses SQLite FTS5 over FIR briefs and evidence text; Qdrant + Amazon Titan embeddings is an optional semantic retrieval upgrade.
- **Knowledge graph** is built at request time from cited case, vehicle, accused and evidence relations.
- **Live UI calls the API** for chat results, case details, graph data, analytics and Leaflet/OpenStreetMap incident markers.
- **Voice input** uses browser-native `SpeechRecognition` / `webkitSpeechRecognition` with an explicit typed fallback.

## Quick start

The browser client is a Next.js application; the data and AI service is Python.

```bash
cd /Users/arnavraj/KSPIC
npm run generate:data       # optional; regenerates deterministic 5,000 records
npm run dev:backend          # terminal 1 - http://127.0.0.1:8000
npm install --prefix frontend
npm run dev:frontend         # terminal 2 - http://127.0.0.1:3000
```

Open [http://127.0.0.1:3000](http://127.0.0.1:3000). Next.js proxies `/api/*` to the Python service, so the frontend can make same-origin requests. Try:

```text
Show burglary cases involving white Swift cars in Bangalore
Show cyber fraud involving fake investment apps
Show missing person cases near Mangalore
```

The first query returns a generated but relationally real 70-case vehicle-linked cluster. Each answer exposes citations, the deterministic rationale, a confidence score and a graph route.

## API surface

| Endpoint | Purpose |
| --- | --- |
| `POST /api/assistant` | Safe SQL + FTS retrieval, evidence-grounded response, citations and confidence |
| `GET /api/search?q=` | Parameterized structured case search |
| `GET /api/rag?q=` | FTS5 retrieval over FIR brief/evidence content |
| `GET /api/cases/{crimeNo}` | CaseMaster and cited evidence detail |
| `GET /api/graph/{crimeNo}` | Case/entity/evidence nodes and relations |
| `GET /api/map` | Geocoded FIR markers, filterable by crime type/district/status |
| `GET /api/analytics` | Aggregate counts from the actual database |

## Amazon Bedrock generation

The assistant works without an API key using a deterministic evidence engine. To enable cost-efficient response drafting with Amazon Nova Lite through Bedrock:

```bash
export AWS_BEARER_TOKEN_BEDROCK='your-key'
npm run dev:backend
```

Amazon Bedrock receives only already-retrieved, limited case context. It cannot change the database count, filters, citations or confidence; the backend retains those deterministic values. This prevents fluent text from fabricating an evidentiary trail.

## Vector search (Qdrant)

Read [docs/bedrock.md](/Users/arnavraj/KSPIC/docs/bedrock.md) for Amazon Bedrock and Qdrant ingestion instructions. The production pattern is hybrid retrieval: jurisdiction-filtered SQL + semantic candidates, followed by citations from the original FIR/evidence records.

## Deploy

Deploy the Next.js frontend with Zoho Catalyst Slate and keep the Python API, Bedrock credential, SQLite database, and Qdrant endpoint on the backend. Follow [the Zoho Slate deployment guide](/Users/arnavraj/KSPIC/docs/zoho-slate-deployment.md).

## Architecture

```text
Officer UI + browser-native voice
              |
              v
Local API / policy boundary
  |              |                 |
  v              v                 v
Safe SQL      FTS / Qdrant      Knowledge graph
  |              |                 |
  +--------------+-----------------+
                 |
                 v
Evidence bundle -> Amazon Bedrock Nova Lite (optional) -> constrained narrative
                 |
                 v
Confidence + citations + audit-ready rationale
```

## Critical safety position

This is investigative decision support, never an enforcement-decision engine. Confidence describes record linkage strength, not culpability. A production deployment must add authentication, RBAC/jurisdiction filtering, immutable audit logs, retention rules, PII controls, human approval gates and formal validation against authorised source data.
