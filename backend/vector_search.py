"""Optional Qdrant semantic-candidate retrieval powered by Bedrock embeddings."""
from __future__ import annotations

import os
from backend import bedrock

COLLECTION = "ksp_case_chunks_bedrock_v1"

def status() -> dict:
    if not bedrock.configured():
        return {"enabled": False, "reason": "AWS_BEARER_TOKEN_BEDROCK is not set"}
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(url=os.getenv("QDRANT_URL", "http://127.0.0.1:6333"), timeout=3)
        if not client.collection_exists(COLLECTION):
            return {"enabled": False, "reason": f"Qdrant collection '{COLLECTION}' is not indexed"}
        return {"enabled": True, "reason": "Qdrant + Amazon Titan embeddings available"}
    except Exception as exc:
        return {"enabled": False, "reason": f"Qdrant unavailable: {type(exc).__name__}"}

def semantic_candidate_numbers(query: str, limit: int = 20) -> tuple[list[str], dict]:
    current = status()
    if not current["enabled"]:
        return [], current
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(url=os.getenv("QDRANT_URL", "http://127.0.0.1:6333"), timeout=15)
        points = client.query_points(COLLECTION, query=bedrock.embed(query), limit=min(limit, 50), with_payload=True).points
        numbers = [point.payload.get("crime_no") for point in points if point.payload.get("crime_no")]
        return numbers, {"enabled": True, "reason": "Semantic vector candidates retrieved", "count": len(numbers)}
    except Exception as exc:
        return [], {"enabled": False, "reason": f"Semantic search unavailable: {type(exc).__name__}"}
