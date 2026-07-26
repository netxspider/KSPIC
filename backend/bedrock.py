"""Minimal Amazon Bedrock bearer-token client using only the standard library."""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

REGION = os.getenv("AWS_REGION", "us-east-1")
NARRATIVE_MODEL = os.getenv("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0")
EMBEDDING_MODEL = os.getenv("BEDROCK_EMBEDDING_MODEL", "amazon.titan-embed-text-v2:0")

def configured() -> bool:
    return bool(os.getenv("AWS_BEARER_TOKEN_BEDROCK"))

def _request(model_id: str, action: str, payload: dict) -> dict:
    token = os.getenv("AWS_BEARER_TOKEN_BEDROCK")
    if not token:
        raise RuntimeError("AWS_BEARER_TOKEN_BEDROCK is not set")
    safe_model = urllib.parse.quote(model_id, safe=".:")
    url = f"https://bedrock-runtime.{REGION}.amazonaws.com/model/{safe_model}/{action}"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Accept": "application/json", "Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())

def narrative(prompt: str) -> str:
    response = _request(NARRATIVE_MODEL, "converse", {
        "messages": [{"role": "user", "content": [{"text": prompt}]}],
        "inferenceConfig": {"maxTokens": 160, "temperature": 0.1},
    })
    return response["output"]["message"]["content"][0]["text"]

def embed(text: str) -> list[float]:
    response = _request(EMBEDDING_MODEL, "invoke", {
        "inputText": text,
        "dimensions": 1024,
        "normalize": True,
    })
    return response["embedding"]
