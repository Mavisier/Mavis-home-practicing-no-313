import hashlib
import json
from datetime import datetime, timezone
from time import perf_counter

from fastapi import HTTPException
from sqlalchemy import func, select

from app.config import get_settings
from app.db import SessionLocal
from app.models import Action, Run, RunEvent, VehicleListing
from app.schemas import ReviewCreate, ReviewResult
from app.services.knowledge import retrieve
from app.services.providers import (
    SYSTEM_PROMPT,
    TOOL_NAMES,
    ProviderConfigurationError,
    ProviderOutputError,
    get_provider,
)
from app.services.vehicle_checks import check_vehicle


def listing_dict(row: VehicleListing) -> dict:
    return {
        "id": row.id,
        "title": row.title,
        "scenario": row.scenario,
        "vehicle": row.vehicle_json,
        "description": row.description,
        "photos": row.photos_json,
    }


def payload_hash(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def append_event(session, run_id, event_type, payload):
    count = (
        session.scalar(select(func.max(RunEvent.sequence)).where(RunEvent.run_id == run_id)) or 0
    )
    session.add(
        RunEvent(run_id=run_id, sequence=count + 1, event_type=event_type, payload_json=payload)
    )
    session.flush()


def process_review(body: ReviewCreate, requester: str):
    started = perf_counter()
    with SessionLocal.begin() as session:
        row = session.scalar(
            select(VehicleListing).where(
                VehicleListing.id == body.listing_id, VehicleListing.requester_id == requester
            )
        )
        if row is None:
            raise HTTPException(404, "Vehicle record not found")
        listing = listing_dict(row)
        run = Run(
            requester_id=requester,
            request_text=body.request_text,
            intent=body.workflow,
            status="processing",
            provider=get_settings().llm_provider,
            model=get_settings().llm_model or "fixture-rules-v1",
            prompt_version="vehicle-review-v3",
        )
        session.add(run)
        session.flush()
        run_id = run.id
        append_event(
            session,
            run_id,
            "request_received",
            {"message": "Araç kontrol talebi alındı.", "listing_id": row.id},
        )
    events = []
    try:
        settings = get_settings()
        if body.listing_id.startswith("REAL-") and (
            settings.llm_provider != "fixture" or settings.embedding_provider != "fixture"
        ):
            raise ProviderConfigurationError(
                "Archived third-party listing samples are restricted to fixture-only review."
            )
        provider = get_provider()
        events.append(("prompt", {"system": SYSTEM_PROMPT, "request": body.model_dump()}))
        calls = provider.plan(body.listing_id, body.workflow, body.request_text)
        if not 1 <= len(calls) <= 2 or not any(call.name == "get_listing" for call in calls):
            raise ValueError("Invalid read-tool plan")
        for call in calls:
            if call.name not in TOOL_NAMES:
                raise ValueError("Tool is outside allowlist")
            if call.listing_id != body.listing_id:
                raise ValueError("Tool target is outside authorized request")
            events.append(("tool_call", call.model_dump()))
            result = (
                listing
                if call.name == "get_listing"
                else {
                    "metadata_only": True,
                    "photo_count": len(listing["photos"]),
                    "angles": [photo["angle"] for photo in listing["photos"]],
                }
            )
            events.append(("tool_result", {"tool": call.name, "result": result}))
        sources, space = retrieve(body.request_text + " " + listing["description"], body.workflow)
        events.append(("retrieval", {"embedding_space": space, "documents": sources}))
        required = (
            {"demo-operations", "listing-information", "photo-guidance"}
            if body.workflow == "listing_review"
            else {"demo-operations", "trink-preparation"}
        )
        if not required.issubset({source["id"] for source in sources}):
            raise ValueError("Knowledge index missing; run ingestion")
        findings = check_vehicle(listing, body.workflow)
        context = {
            "listing": listing,
            "workflow": body.workflow,
            "findings": findings,
            "sources": sources,
        }
        if get_settings().llm_provider == "ollama":
            used_source_ids = {finding["source_id"] for finding in findings}
            context = {
                "workflow": body.workflow,
                "findings": findings,
                "sources": [source for source in sources if source["id"] in used_source_ids],
            }
        events.append(
            ("prompt", {"system": SYSTEM_PROMPT, "context": context, "stage": "explanation"})
        )
        narrative = provider.explain(context)
        verdict = (
            "needs_information"
            if any(f["code"].startswith("missing_") for f in findings)
            else "needs_review"
            if findings
            else "consistent"
        )
        response = {
            "listing": listing,
            "workflow": body.workflow,
            "verdict": verdict,
            "findings": findings,
            "narrative": narrative.model_dump(),
            "sources": sources,
            "mode": get_settings().llm_provider,
            "embedding_space": space,
            "explanation_kind": (
                "fixture"
                if get_settings().llm_provider == "fixture"
                else "approved_empty"
                if get_settings().llm_provider == "ollama" and not findings
                else "local_summary"
                if get_settings().llm_provider == "ollama"
                else "remote_narrative"
            ),
            "latency_ms": round((perf_counter() - started) * 1000),
            "limitations": [
                "Fotoğraflardan hasar veya açı çıkarımı yapılmadı.",
                "İlan beyanları bağımsız olarak doğrulanmadı.",
                "Fiyat, gerçek yayın veya satın alma kararı üretilmez.",
            ],
        }
        response = ReviewResult.model_validate(response).model_dump(mode="json")
        with SessionLocal.begin() as session:
            run = session.get(Run, run_id)
            for event_type, payload in events:
                append_event(session, run_id, event_type, payload)
            if findings:
                arguments = {
                    "listing_id": listing["id"],
                    "listing_snapshot_hash": payload_hash(listing),
                    "workflow": body.workflow,
                    "findings": findings,
                    "seller_message": narrative.seller_message,
                }
                session.add(
                    Action(
                        run_id=run_id,
                        tool_name="create_review_task",
                        arguments_json=arguments,
                        payload_hash=payload_hash(arguments),
                    )
                )
                run.status = "awaiting_approval"
                append_event(
                    session,
                    run_id,
                    "action_proposed",
                    {"message": "Yerel inceleme görevi önerildi; insan onayı bekleniyor."},
                )
            else:
                run.status = "answered"
            run.final_response_json = response
            run.finished_at = datetime.now(timezone.utc)
            append_event(session, run_id, "final_response", response)
    except Exception as error:
        with SessionLocal.begin() as session:
            run = session.get(Run, run_id)
            for event_type, payload in events:
                append_event(session, run_id, event_type, payload)
            run.status = "failed"
            run.finished_at = datetime.now(timezone.utc)
            run.final_response_json = {
                "error": str(error)
                if isinstance(error, (ProviderConfigurationError, ProviderOutputError))
                else "Kontrol tamamlanamadı. Model ayarlarını ve bilgi indeksini kontrol edin.",
                "mode": get_settings().llm_provider,
            }
            append_event(
                session,
                run_id,
                "workflow_failed",
                {"message": "Kontrol güvenli şekilde durduruldu; aksiyon uygulanmadı."},
            )
            if isinstance(error, ProviderOutputError):
                append_event(
                    session,
                    run_id,
                    "model_output_rejected",
                    {"reason": str(error), "candidate": error.candidate},
                )
    return run_id
