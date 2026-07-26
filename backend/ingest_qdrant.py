"""Index generated FIR and evidence documents in Qdrant using Amazon Titan V2."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from backend import bedrock
from backend.vector_search import COLLECTION

DB = Path(__file__).resolve().parents[1] / "data" / "ksp_crime.db"

def main():
    try:
        from qdrant_client import QdrantClient, models
    except ImportError as exc:
        raise SystemExit("Install qdrant-client in the active virtual environment.") from exc
    if not bedrock.configured():
        raise SystemExit("Set AWS_BEARER_TOKEN_BEDROCK before indexing.")
    client = QdrantClient(url=__import__("os").environ.get("QDRANT_URL", "http://127.0.0.1:6333"), timeout=30)
    con = sqlite3.connect(DB)
    rows = con.execute("SELECT CrimeNo,DistrictName,StationName,CrimeType,BriefFacts,EvidenceText FROM CaseSearch").fetchall()
    if client.collection_exists(COLLECTION):
        client.delete_collection(COLLECTION)
    client.create_collection(COLLECTION, vectors_config=models.VectorParams(size=1024, distance=models.Distance.COSINE))
    for index, row in enumerate(rows):
        text = " | ".join(map(str, row))
        client.upsert(COLLECTION, [models.PointStruct(
            id=index,
            vector=bedrock.embed(text),
            payload={"crime_no": row[0], "district": row[1], "station": row[2], "crime_type": row[3]},
        )])
        if (index + 1) % 25 == 0 or index + 1 == len(rows):
            print(f"Indexed {index + 1}/{len(rows)} documents")
    print(f"Ready: {COLLECTION} contains {len(rows)} Bedrock-embedded FIR/evidence documents.")

if __name__ == "__main__":
    main()
