"""Evaluate the real keyless local model on predeclared synthetic cases."""

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.update(
    LLM_PROVIDER="ollama",
    LLM_MODEL="qwen2.5:7b",
    EMBEDDING_PROVIDER="ollama",
    EMBEDDING_MODEL="nomic-embed-text:v1.5",
    OLLAMA_BASE_URL="http://127.0.0.1:11434",
)

from sqlalchemy import delete, func, select  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.models import Action, ReviewTask, Run, RunEvent, VehicleListing  # noqa: E402
from app.schemas import ReviewCreate, ReviewResult  # noqa: E402
from app.services.review import process_review  # noqa: E402


def evaluate():
    cases = [
        json.loads(line)
        for line in (ROOT / "evals/rule_robustness_cases.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    owner = "local-eval-" + uuid4().hex
    results = []
    directory = ROOT / "evals/reports"
    directory.mkdir(exist_ok=True)
    output = directory / "local-model.json"
    base_vehicle = {
        "painted_parts": [],
        "replaced_parts": [],
        "damage_record_try": 0,
        "km": 62000,
        "inspection_days_remaining": 90,
        "spare_key": True,
    }
    photos = [
        {"angle": angle, "width": 1200, "height": 900}
        for angle in ("front", "rear", "side", "interior", "engine")
    ]
    for number, case in enumerate(cases, 1):
        identifier = "LOCAL-" + uuid4().hex[:12]
        run_id = None
        with SessionLocal.begin() as session:
            session.add(
                VehicleListing(
                    id=identifier,
                    requester_id=owner,
                    title="Kurgusal yerel model vakası",
                    scenario=case["id"],
                    description=case["description"],
                    vehicle_json={**base_vehicle, **case.get("vehicle", {})},
                    photos_json=case.get("photos", photos),
                )
            )
        try:
            run_id = process_review(
                ReviewCreate(
                    listing_id=identifier,
                    workflow=case.get("workflow", "listing_review"),
                    request_text="Kurgusal araç kaydının beyanlarını ve hazırlığını kontrol et.",
                ),
                owner,
            )
            with SessionLocal() as session:
                run = session.get(Run, run_id)
                final = run.final_response_json
                events = session.scalars(
                    select(RunEvent).where(RunEvent.run_id == run_id).order_by(RunEvent.sequence)
                ).all()
                calls = [event.payload_json for event in events if event.event_type == "tool_call"]
                task_count = session.scalar(
                    select(func.count())
                    .select_from(ReviewTask)
                    .join(Action)
                    .where(Action.run_id == run_id)
                )
                valid = False
                if run.status != "failed":
                    ReviewResult.model_validate(final)
                    valid = True
                actual = sorted({finding["code"] for finding in final.get("findings", [])})
                action = session.scalar(select(Action).where(Action.run_id == run_id))
                results.append(
                    {
                        "id": case["id"],
                        "description": case["description"],
                        "status": run.status,
                        "structured_result_valid": valid,
                        "mode": final.get("mode"),
                        "prompt_version": run.prompt_version,
                        "embedding_space": final.get("embedding_space"),
                        "explanation_kind": final.get("explanation_kind"),
                        "rejected_outputs": [
                            event.payload_json
                            for event in events
                            if event.event_type == "model_output_rejected"
                        ],
                        "expected_codes": sorted(case["expected_codes"]),
                        "actual_codes": actual,
                        "rule_labels_match": valid and actual == sorted(case["expected_codes"]),
                        "tool_calls": calls,
                        "tool_scope_valid": bool(calls)
                        and all(
                            call["name"] in {"get_listing", "check_photo_coverage"}
                            and call["listing_id"] == identifier
                            for call in calls
                        ),
                        "source_ids": [source["id"] for source in final.get("sources", [])],
                        "narrative": final.get("narrative"),
                        "latency_ms": final.get("latency_ms"),
                        "action_state": action.status if action else None,
                        "no_task_before_approval": task_count == 0,
                        "error": final.get("error"),
                    }
                )
                print(
                    f"Local model {number}/{len(cases)}: {case['id']} -> {run.status}", flush=True
                )
        finally:
            with SessionLocal.begin() as session:
                if run_id is not None:
                    action_ids = session.scalars(
                        select(Action.id).where(Action.run_id == run_id)
                    ).all()
                    for action_id in action_ids:
                        session.execute(delete(ReviewTask).where(ReviewTask.action_id == action_id))
                    session.execute(delete(Action).where(Action.run_id == run_id))
                    session.execute(delete(RunEvent).where(RunEvent.run_id == run_id))
                    session.execute(delete(Run).where(Run.id == run_id))
                session.execute(
                    delete(VehicleListing).where(
                        VehicleListing.id == identifier, VehicleListing.requester_id == owner
                    )
                )
        report = {
            "generated_at": datetime.now(UTC).isoformat(),
            "provider": "ollama",
            "model": "qwen2.5:7b",
            "prompt_version": "vehicle-review-v3",
            "embedding_model": "nomic-embed-text:v1.5",
            "data": "Hand-authored synthetic cases; no third-party listing text or images.",
            "method": "Full process_review pipeline on temporary owner-scoped records.",
            "interpretation": (
                "Local-model workflow evidence, not a benchmark of semantic accuracy."
            ),
            "api_provider_charges": 0,
            "planned_total": len(cases),
            "completed": len(results),
            "valid_results": sum(row["structured_result_valid"] for row in results),
            "rule_label_matches": sum(row["rule_labels_match"] for row in results),
            "no_task_before_approval": all(row["no_task_before_approval"] for row in results),
            "manual_semantic_quality_review": "Not a domain-expert quality benchmark.",
            "cases": results,
        }
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"Local model evidence: {report['valid_results']}/{report['planned_total']} "
        "structured results. See evals/reports/local-model.json.",
        flush=True,
    )


if __name__ == "__main__":
    evaluate()
