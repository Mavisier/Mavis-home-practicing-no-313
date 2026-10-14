import hashlib
import math
import re
from pathlib import Path

from sqlalchemy import or_, select

from app.config import PROJECT_ROOT, get_settings
from app.db import SessionLocal
from app.models import KnowledgeChunk


def embed(text: str) -> tuple[list[float], str]:
    settings = get_settings()
    if settings.embedding_provider == "openai":
        import httpx

        if (
            settings.openai_api_key is None
            or not settings.openai_api_key.get_secret_value().strip()
        ):
            from app.services.providers import ProviderConfigurationError

            raise ProviderConfigurationError(
                "Selected embedding provider has no API key configured."
            )
        with httpx.Client(timeout=20) as client:
            response = client.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {settings.openai_api_key.get_secret_value()}"},
                json={"model": settings.embedding_model, "input": text},
            )
            response.raise_for_status()
            return response.json()["data"][0]["embedding"], f"openai:{settings.embedding_model}"
    # A reproducible token-hash vector for the keyless demo. NOT a neural embedding.
    vector = [0.0] * 128
    for token in re.findall(r"\w+", text.casefold()):
        slot = int.from_bytes(hashlib.sha256(token.encode()).digest()[:4], "big") % 128
        vector[slot] += 1.0
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector], "fixture:token-hash-128-v1"


def ingest(directory: Path | None = None) -> int:
    paths = sorted((directory or PROJECT_ROOT / "data/company_docs").glob("*.md"))
    prepared = []
    for path in paths:
        _empty, header, body = path.read_text(encoding="utf-8").split("---", 2)
        metadata = dict(line.split(":", 1) for line in header.strip().splitlines())
        metadata = {key.strip(): value.strip() for key, value in metadata.items()}
        if not body.strip() or len(body) > 12000:
            raise ValueError(
                "Use a non-empty short document; split larger documents before ingestion"
            )
        if metadata["workflow"] not in {"listing_review", "trink_readiness", "shared"}:
            raise ValueError("Unsupported knowledge workflow")
        if metadata["source_kind"] not in {"public_summary", "synthetic_policy"}:
            raise ValueError("Unsupported knowledge source kind")
        vector, space = embed(body)
        prepared.append((metadata, body, vector, space))
    # Prepare all vectors first: one provider failure must not partially replace the index.
    with SessionLocal.begin() as session:
        for metadata, body, vector, space in prepared:
            existing = session.get(KnowledgeChunk, metadata["id"])
            if existing is None:
                existing = KnowledgeChunk(id=metadata["id"])
                session.add(existing)
            existing.title = metadata["title"]
            existing.workflow = metadata["workflow"]
            existing.body = body.strip()
            existing.source_url = metadata.get("source_url") or None
            existing.source_kind = metadata["source_kind"]
            existing.source_version = metadata["version"]
            existing.embedding = vector
            existing.embedding_space = space
    return len(paths)


def retrieve(query: str, workflow: str) -> tuple[list[dict], str]:
    vector, space = embed(query)
    with SessionLocal() as session:
        chunks = session.scalars(
            select(KnowledgeChunk)
            .where(KnowledgeChunk.embedding_space == space)
            .where(or_(KnowledgeChunk.workflow == workflow, KnowledgeChunk.workflow == "shared"))
            .order_by(KnowledgeChunk.embedding.cosine_distance(vector))
            .limit(3)
        ).all()
        return [
            {
                "id": row.id,
                "title": row.title,
                "body": row.body,
                "url": row.source_url,
                "kind": row.source_kind,
                "version": row.source_version,
            }
            for row in chunks
        ], space
