"""Keyless native Ollama adapter restricted to local origins."""

import json
import re
from urllib.parse import urlsplit

import httpx
from pydantic import BaseModel, ConfigDict, Field

from app.config import get_settings
from app.schemas import Narrative
from app.services.providers import (
    ARG_SCHEMA,
    SYSTEM_PROMPT,
    TOOL_NAMES,
    FixtureProvider,
    ProviderConfigurationError,
    ProviderOutputError,
    ReadCall,
)
from app.services.vehicle_checks import normalized


class SummaryDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: str = Field(min_length=1, max_length=1200)


def ollama_origin():
    value = get_settings().ollama_base_url.rstrip("/")
    parsed = urlsplit(value)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "localhost", "host.docker.internal"}
        or parsed.username
        or parsed.password
        or parsed.path
        or parsed.query
        or parsed.fragment
    ):
        raise ProviderConfigurationError("Ollama requires an explicit local HTTP origin.")
    return value


class OllamaProvider:
    def __init__(self):
        self.settings = get_settings()
        self.origin = ollama_origin()
        if not self.settings.llm_model.strip() or "cloud" in self.settings.llm_model.casefold():
            raise ProviderConfigurationError("Ollama requires a local LLM_MODEL.")

    def call(self, payload):
        with httpx.Client(timeout=120, follow_redirects=False, trust_env=False) as client:
            response = client.post(
                self.origin + "/api/chat",
                json={
                    "model": self.settings.llm_model,
                    "stream": False,
                    "options": {"temperature": 0, "num_ctx": 4096, "num_predict": 1200},
                    **payload,
                },
            )
            response.raise_for_status()
            return response.json()

    def plan(self, listing_id, workflow, request):
        result = self.call(
            {
                "messages": [
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT + " Bu aşamada yalnızca okuma aracı çağrısı üret. "
                        "get_listing zorunlu. listing_review için check_photo_coverage da seç. "
                        "En fazla iki araç çağır; verilen listing_id değerini aynen kullan.",
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            {"listing_id": listing_id, "workflow": workflow, "request": request},
                            ensure_ascii=False,
                        ),
                    },
                ],
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": name,
                            "description": "Read only the supplied synthetic vehicle record.",
                            "parameters": ARG_SCHEMA,
                        },
                    }
                    for name in TOOL_NAMES
                ],
            }
        )
        return [
            ReadCall(name=call["function"]["name"], **call["function"]["arguments"])
            for call in result["message"].get("tool_calls", [])
        ]

    def explain(self, context):
        approved = FixtureProvider().explain(context)
        if not context["findings"]:
            return approved  # Deliberate empty-result policy, never an error fallback.
        source_ids = {finding["source_id"] for finding in context["findings"]}
        focused = {
            "workflow": context["workflow"],
            "findings": context["findings"],
            "sources": [source for source in context["sources"] if source["id"] in source_ids],
        }
        result = self.call(
            {
                "messages": [
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT + " Yalnızca summary alanını içeren JSON üret. "
                        "En fazla iki kısa cümleyle verilen bulguları açıkla. "
                        "Araç durumu veya satıcı niyeti hakkında ek değerlendirme yapma.",
                    },
                    {"role": "user", "content": json.dumps(focused, ensure_ascii=False)},
                ],
                "format": SummaryDraft.model_json_schema(),
            }
        )
        draft = SummaryDraft.model_validate_json(result["message"]["content"])
        text = normalized(draft.summary)
        if re.search(r"\b(?:kasit\w*|gizle\w*|dolandir\w*|durust\w*)\b", text):
            raise ProviderOutputError("Local summary mentions seller intent.", draft.model_dump())
        if re.search(r"fotograf\w*.{0,100}arac\w*.{0,60}(?:gosteriyor|dogruluyor)", text):
            raise ProviderOutputError("Local summary claims image evidence.", draft.model_dump())
        return Narrative(
            summary=draft.summary,
            seller_message=approved.seller_message,
            questions=approved.questions,
        )
