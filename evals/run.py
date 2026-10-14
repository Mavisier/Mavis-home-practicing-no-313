"""Reproducible offline workflow evaluation; never enables a live provider."""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ["LLM_PROVIDER"] = "fixture"
os.environ["EMBEDDING_PROVIDER"] = "fixture"

from sqlalchemy import delete, select  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.models import Action, ReviewTask, Run, RunEvent  # noqa: E402
from app.schemas import ReviewCreate, ReviewResult  # noqa: E402
from app.services.review import process_review  # noqa: E402


def evaluate():
    results = []
    for line in (ROOT / "evals/cases.jsonl").read_text().splitlines():
        case = json.loads(line)
        run_id = process_review(
            ReviewCreate(
                listing_id=case["listing_id"],
                workflow=case["workflow"],
                request_text=case.get(
                    "request_text",
                    "Eval: araç beyanı fotoğraf kapsamı ve ekspertiz hazırlığını kontrol et.",
                ),
            ),
            "demo-requester",
        )
        with SessionLocal.begin() as session:
            run = session.get(Run, run_id)
            final = run.final_response_json
            source_ids = {source["id"] for source in final.get("sources", [])}
            checks = {
                "typed_route": run.intent == case["workflow"],
                "status": run.status == case["expected_status"],
                "findings": {f["code"] for f in final.get("findings", [])}
                == set(case["expected_codes"]),
                "citations": all(f["source_id"] in source_ids for f in final.get("findings", [])),
                "structured_answer": bool(final.get("narrative", {}).get("summary")),
                "structured_schema": bool(ReviewResult.model_validate(final)),
                "supporting_sources": {"demo-operations", "trink-preparation"}.issubset(source_ids)
                if case["workflow"] == "trink_readiness"
                else {"demo-operations", "listing-information", "photo-guidance"}.issubset(
                    source_ids
                ),
                "allowed_tool_selection": {
                    e.payload_json.get("name")
                    for e in session.scalars(
                        select(RunEvent).where(
                            RunEvent.run_id == run_id, RunEvent.event_type == "tool_call"
                        )
                    )
                }
                == (
                    {"get_listing"}
                    if case["workflow"] == "trink_readiness"
                    else {"get_listing", "check_photo_coverage"}
                ),
                "no_execution": session.scalar(select(Action.status).where(Action.run_id == run_id))
                in {None, "pending_approval"},
            }
            results.append(
                {
                    "id": case["id"],
                    "passed": all(checks.values()),
                    "checks": checks,
                    "latency_ms": final.get("latency_ms"),
                }
            )
            # Remove only this runner's temporary records; no UI/demo runs are deleted.
            for action in session.scalars(select(Action).where(Action.run_id == run_id)).all():
                session.execute(delete(ReviewTask).where(ReviewTask.action_id == action.id))
                session.delete(action)
            session.flush()
            session.execute(delete(RunEvent).where(RunEvent.run_id == run_id))
            session.delete(run)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "fixture",
        "interpretation": "Deterministic workflow checks, not live LLM response-quality evidence.",
        "passed": sum(row["passed"] for row in results),
        "total": len(results),
        "cases": results,
    }
    directory = ROOT / "evals/reports"
    directory.mkdir(exist_ok=True)
    path = directory / "latest.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Fixture evaluation: {report['passed']}/{report['total']} passed. Report: {path}")
    if report["passed"] != report["total"]:
        raise SystemExit(1)


if __name__ == "__main__":
    evaluate()
