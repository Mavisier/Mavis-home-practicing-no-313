from uuid import uuid4

import httpx
import pytest
from pydantic import ValidationError

from app.config import get_settings
from app.db import SessionLocal
from app.models import VehicleListing
from app.services.knowledge import embed
from app.services.local_model import OllamaProvider, ollama_origin
from app.services.providers import FixtureProvider, ProviderConfigurationError, ReadCall


def mock_local_api(monkeypatch, response_json):
    original_client = httpx.Client
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json=response_json)

    monkeypatch.setattr(
        httpx,
        "Client",
        lambda *args, **kwargs: original_client(
            *args, transport=httpx.MockTransport(handler), **kwargs
        ),
    )
    return seen


@pytest.mark.parametrize(
    "origin",
    [
        "https://example.invalid",
        "http://example.invalid",
        "http://user:password@localhost:11434",
        "http://localhost:11434/api",
        "http://localhost:11434?token=test-only",
        "http://localhost:11434#fragment",
    ],
)
def test_ollama_rejects_remote_or_ambiguous_origins(monkeypatch, origin):
    monkeypatch.setattr(get_settings(), "ollama_base_url", origin)
    with pytest.raises(ProviderConfigurationError):
        ollama_origin()


@pytest.mark.parametrize("model", ["", "  ", "example-cloud"])
def test_ollama_requires_explicit_local_model(monkeypatch, model):
    monkeypatch.setattr(get_settings(), "llm_model", model)
    with pytest.raises(ProviderConfigurationError):
        OllamaProvider()


def test_ollama_tool_response_uses_native_schema_and_no_provider_credential(monkeypatch):
    monkeypatch.setattr(get_settings(), "llm_model", "test-only-local-model")
    seen = mock_local_api(
        monkeypatch,
        {
            "message": {
                "tool_calls": [
                    {"function": {"name": "get_listing", "arguments": {"listing_id": "ILAN-1001"}}}
                ]
            }
        },
    )
    calls = OllamaProvider().plan("ILAN-1001", "listing_review", "test-only request")
    assert calls[0].name == "get_listing"
    assert calls[0].listing_id == "ILAN-1001"
    assert seen[0].url.path == "/api/chat"
    assert seen[0].url.host == "127.0.0.1"
    assert "authorization" not in seen[0].headers
    assert "x-api-key" not in seen[0].headers


def test_ollama_unknown_tool_is_rejected(monkeypatch):
    monkeypatch.setattr(get_settings(), "llm_model", "test-only-local-model")
    mock_local_api(
        monkeypatch,
        {
            "message": {
                "tool_calls": [
                    {"function": {"name": "run_shell", "arguments": {"listing_id": "ILAN-1001"}}}
                ]
            }
        },
    )
    with pytest.raises(ValidationError):
        OllamaProvider().plan("ILAN-1001", "listing_review", "test-only request")


def summary_context():
    return {
        "workflow": "listing_review",
        "findings": [{"question": "Approved question", "source_id": "test-only-source"}],
        "sources": [{"id": "test-only-source", "body": "Synthetic guidance."}],
    }


def test_ollama_generates_summary_and_backend_retains_the_approved_draft(monkeypatch):
    monkeypatch.setattr(get_settings(), "llm_model", "test-only-local-model")
    mock_local_api(monkeypatch, {"message": {"content": '{"summary":"Özet"}'}})
    context = summary_context()
    narrative = OllamaProvider().explain(context)
    approved = FixtureProvider().explain(context)
    assert narrative.summary == "Özet"
    assert narrative.questions == approved.questions
    assert narrative.seller_message == approved.seller_message


def test_local_model_cannot_add_an_unapproved_question(monkeypatch):
    monkeypatch.setattr(get_settings(), "llm_model", "test-only-local-model")
    mock_local_api(
        monkeypatch,
        {"message": {"content": '{"summary":"Summary","questions":["Unsupported question"]}'}},
    )
    with pytest.raises(ValidationError):
        OllamaProvider().explain(summary_context())


def test_empty_result_uses_approved_wording_without_extra_model_generation(monkeypatch):
    monkeypatch.setattr(get_settings(), "llm_model", "test-only-local-model")
    seen = mock_local_api(
        monkeypatch,
        {"message": {"content": '{"summary":"İlan yayınlandı"}'}},
    )
    approved = FixtureProvider().explain({"findings": []})
    assert OllamaProvider().explain({"findings": []}) == approved
    assert seen == []


@pytest.mark.parametrize(
    "summary,reason",
    [
        ("Satıcı kusuru gizlemeye çalışıyor.", "seller intent"),
        ("Fotoğraflar aracın hasar durumunu doğruluyor.", "image evidence"),
    ],
)
def test_local_summary_policy_rejects_explicit_unsupported_claims(monkeypatch, summary, reason):
    monkeypatch.setattr(get_settings(), "llm_model", "test-only-local-model")
    import json

    mock_local_api(monkeypatch, {"message": {"content": json.dumps({"summary": summary})}})
    from app.services.providers import ProviderOutputError

    with pytest.raises(ProviderOutputError, match=reason):
        OllamaProvider().explain(summary_context())


def test_local_neural_embedding_has_separate_space_and_no_truncation(monkeypatch):
    monkeypatch.setattr(get_settings(), "embedding_provider", "ollama")
    monkeypatch.setattr(get_settings(), "embedding_model", "test-only-embedding")
    seen = mock_local_api(monkeypatch, {"embeddings": [[0.1, 0.2, 0.3]]})
    vector, space = embed("synthetic text")
    assert vector == [0.1, 0.2, 0.3]
    assert space == "ollama:test-only-embedding"
    assert seen[0].url.path == "/api/embed"
    assert b'"truncate":false' in seen[0].content


def test_rejected_local_summary_cannot_create_a_proposal(client, headers, prefix, monkeypatch):
    monkeypatch.setattr(get_settings(), "llm_provider", "ollama")
    monkeypatch.setattr(get_settings(), "llm_model", "test-only-local-model")
    monkeypatch.setattr(
        OllamaProvider,
        "plan",
        lambda self, listing_id, workflow, request: [
            ReadCall(name="get_listing", listing_id=listing_id)
        ],
    )
    monkeypatch.setattr(
        OllamaProvider,
        "call",
        lambda self, payload: {
            "message": {"content": '{"summary":"Satıcı kusuru gizlemeye çalışıyor."}'}
        },
    )
    response = client.post(
        "/api/reviews",
        headers=headers,
        json={"listing_id": "ILAN-1001", "workflow": "listing_review", "request_text": prefix},
    )
    run = response.json()
    assert run["status"] == "failed"
    assert run["action"] is None
    assert any(event["event_type"] == "model_output_rejected" for event in run["events"])


@pytest.mark.parametrize("vector", [[], [True], [None], ["invalid"]])
def test_invalid_local_embeddings_are_not_stored(monkeypatch, vector):
    monkeypatch.setattr(get_settings(), "embedding_provider", "ollama")
    monkeypatch.setattr(get_settings(), "embedding_model", "test-only-embedding")
    mock_local_api(monkeypatch, {"embeddings": [vector]})
    with pytest.raises(ValueError, match="Invalid local embedding"):
        embed("synthetic text")


@pytest.mark.parametrize("generation,embedding", [("ollama", "fixture"), ("fixture", "ollama")])
def test_archived_sample_is_blocked_before_any_model_call(
    client, headers, prefix, monkeypatch, generation, embedding
):
    identifier = "REAL-TEST-" + uuid4().hex[:12]
    with SessionLocal.begin() as session:
        session.add(
            VehicleListing(
                id=identifier,
                requester_id="demo-requester",
                title="Synthetic policy-boundary fixture",
                scenario="test-only",
                vehicle_json={},
                description="Synthetic test text.",
                photos_json=[],
            )
        )
    monkeypatch.setattr(get_settings(), "llm_provider", generation)
    monkeypatch.setattr(get_settings(), "embedding_provider", embedding)
    try:
        response = client.post(
            "/api/reviews",
            headers=headers,
            json={"listing_id": identifier, "workflow": "listing_review", "request_text": prefix},
        )
        run = response.json()
        assert run["status"] == "failed"
        assert "fixture-only" in run["final_response_json"]["error"]
        assert run["action"] is None
        assert not any(event["event_type"] == "tool_call" for event in run["events"])
    finally:
        with SessionLocal.begin() as session:
            session.delete(session.get(VehicleListing, identifier))
