from uuid import uuid4

import pytest
from sqlalchemy import delete

from app.db import SessionLocal
from app.models import KnowledgeChunk
from app.services import knowledge


def document(identifier, body="A short synthetic policy."):
    return (
        f"---\nid: {identifier}\ntitle: Atomic fixture\nworkflow: shared\n"
        f"source_kind: synthetic_policy\nversion: new\nsource_url:\n---\n{body}"
    )


def test_embedding_failure_does_not_partially_replace_existing_index(tmp_path, monkeypatch):
    first, second = "atomic-" + uuid4().hex, "atomic-" + uuid4().hex
    (tmp_path / "a.md").write_text(document(first))
    (tmp_path / "b.md").write_text(document(second))
    with SessionLocal.begin() as session:
        session.add(
            KnowledgeChunk(
                id=first,
                title="Old",
                workflow="shared",
                body="Old",
                source_url=None,
                source_kind="synthetic_policy",
                source_version="old",
                embedding=[1.0] + [0.0] * 127,
                embedding_space="test-only-space",
            )
        )
    counter = 0

    def failed_second_embedding(text):
        nonlocal counter
        counter += 1
        if counter == 2:
            raise ValueError("Simulated provider failure")
        return [1.0] + [0.0] * 127, "test-only-space"

    monkeypatch.setattr(knowledge, "embed", failed_second_embedding)
    try:
        with pytest.raises(ValueError):
            knowledge.ingest(tmp_path)
        with SessionLocal() as session:
            assert session.get(KnowledgeChunk, first).source_version == "old"
            assert session.get(KnowledgeChunk, second) is None
    finally:
        with SessionLocal.begin() as session:
            session.execute(delete(KnowledgeChunk).where(KnowledgeChunk.id.in_([first, second])))


def test_oversized_document_is_rejected_without_embedding_call(tmp_path, monkeypatch):
    (tmp_path / "a.md").write_text(document("oversize-test", "x" * 12001))
    monkeypatch.setattr(
        knowledge, "embed", lambda text: pytest.fail("Must reject before embedding")
    )
    with pytest.raises(ValueError, match="short document"):
        knowledge.ingest(tmp_path)
