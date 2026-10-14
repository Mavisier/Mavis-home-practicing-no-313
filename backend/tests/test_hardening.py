from types import SimpleNamespace

import pytest
from pydantic import SecretStr, ValidationError

from app.config import get_settings
from app.schemas import Narrative, ReviewCreate
from app.services.knowledge import embed
from app.services.providers import ProviderConfigurationError, RemoteProvider


@pytest.mark.parametrize(
    "provider,field", [("openai", "openai_api_key"), ("anthropic", "anthropic_api_key")]
)
@pytest.mark.parametrize("value", [None, SecretStr(""), SecretStr("   ")])
def test_live_provider_requires_nonblank_key_before_network(monkeypatch, provider, field, value):
    monkeypatch.setattr(get_settings(), field, value)
    monkeypatch.setattr(get_settings(), "llm_model", "test-only-model")
    with pytest.raises(ProviderConfigurationError):
        RemoteProvider(provider)


def test_missing_embedding_key_fails_before_network(monkeypatch):
    monkeypatch.setattr(get_settings(), "embedding_provider", "openai")
    monkeypatch.setattr(get_settings(), "openai_api_key", SecretStr(""))
    with pytest.raises(ProviderConfigurationError):
        embed("fixture text")


def test_live_failure_is_persisted_without_fixture_fallback(client, headers, prefix, monkeypatch):
    monkeypatch.setattr(get_settings(), "llm_provider", "openai")
    monkeypatch.setattr(get_settings(), "openai_api_key", None)
    result = client.post(
        "/api/reviews",
        headers=headers,
        json={"listing_id": "ILAN-1001", "workflow": "listing_review", "request_text": prefix},
    ).json()
    assert result["status"] == "failed"
    assert result["final_response_json"]["mode"] == "openai"
    assert "API key" in result["final_response_json"]["error"]
    assert result["action"] is None


@pytest.mark.parametrize("identifier", ["../private", "https://example.invalid", "x" * 41])
def test_listing_identifiers_are_bounded_and_not_paths(identifier):
    with pytest.raises(ValidationError):
        ReviewCreate(listing_id=identifier, workflow="listing_review", request_text="valid request")


def test_unstructured_or_unbounded_narrative_is_rejected():
    with pytest.raises(ValidationError):
        Narrative(summary="x" * 4001, seller_message="draft", questions=[])


def test_unknown_tool_from_provider_cannot_run(client, headers, prefix, monkeypatch):
    from app.services.providers import FixtureProvider

    monkeypatch.setattr(
        FixtureProvider,
        "plan",
        lambda *args: [
            SimpleNamespace(name="get_listing", listing_id="ILAN-1001", model_dump=lambda: {}),
            SimpleNamespace(name="run_shell", listing_id="ILAN-1001"),
        ],
    )
    result = client.post(
        "/api/reviews",
        headers=headers,
        json={"listing_id": "ILAN-1001", "workflow": "listing_review", "request_text": prefix},
    ).json()
    assert result["status"] == "failed"
    assert result["action"] is None
