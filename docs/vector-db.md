# Vector database setup - Qdrant + Amazon Bedrock embeddings

The prototype works immediately with SQLite FTS retrieval. Add Qdrant when you want semantic retrieval over FIR briefs, evidence notes, and witness statements.

## 1. Start Qdrant locally (optional)

Qdrant is not required to run the application. The default RAG path uses SQLite FTS5. Add Qdrant only when you want semantic vector retrieval.

First open **Docker Desktop** and wait until it says the engine is running. Verify it with:

```bash
docker info
```

This machine does not have a Docker Compose plugin, so use the direct command below:

```bash
docker run -d --name ksp-qdrant \
  -p 6333:6333 -p 6334:6334 \
  -v ksp_qdrant_storage:/qdrant/storage \
  qdrant/qdrant:v1.13.2
```

To stop it later, run `docker stop ksp-qdrant`. To start it again, run `docker start ksp-qdrant`.

If Docker Compose becomes available later, either of these alternatives also work:

```bash
# Docker Desktop / Compose v2
docker compose -f docker-compose.qdrant.yml up -d

# Legacy Docker Compose (use this if `docker compose` reports an unknown flag)
docker-compose -f docker-compose.qdrant.yml up -d
```

Qdrant is then available at `http://localhost:6333/dashboard`.

## 2. Create the synthetic crime database

```bash
python3 -m backend.generate_data --count 5000
```

## 3. Configure Amazon Bedrock and install the optional vector packages

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements-vector.txt
export AWS_BEARER_TOKEN_BEDROCK='your-key'
export AWS_REGION='us-east-1'
export QDRANT_URL='http://localhost:6333'
python3 -m backend.ingest_qdrant
```

`backend.ingest_qdrant` creates `ksp_case_chunks_bedrock_v1`, with one vector per retrieved FIR/evidence document. It uses Amazon Titan Text Embeddings V2 at 1,024 dimensions and payload metadata for crime number, district, and crime type.

For the complete Bedrock model and safety setup, read [bedrock.md](/Users/arnavraj/KSPIC/docs/bedrock.md).

## Production controls

- Keep FIR metadata and vector payloads in a private VPC; do not send raw PII to third-party embedding services without an approved data-processing agreement.
- Filter Qdrant queries by the officer's jurisdiction and role before retrieving context.
- Treat vector results as candidates only. The SQL record and original evidence remain the cited authority.
- Log query ID, retrieval IDs, model version, and final cited sources for audit.
