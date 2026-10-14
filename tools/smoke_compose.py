"""Exercise fixture Compose HTTP, human approval and native PostgreSQL concurrency."""

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from threading import Barrier
from uuid import UUID, uuid4

import httpx
from sqlalchemy import delete, func, select, text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import get_settings  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.models import Action, ReviewTask, Run, RunEvent, VehicleListing  # noqa: E402


def verify():
    settings = get_settings()
    database = make_url(settings.database_url)
    if (
        database.host not in {"127.0.0.1", "localhost"}
        or database.port != 5433
        or database.database != "workflow"
        or settings.llm_provider != "fixture"
        or settings.embedding_provider != "fixture"
        or settings.demo_approver_token is None
    ):
        raise ValueError("Use the documented local fixture Compose verification settings.")
    headers = {"X-Demo-Token": settings.demo_requester_token.get_secret_value()}
    approval = {
        **headers,
        "X-Demo-Approver-Token": settings.demo_approver_token.get_secret_value(),
    }
    origin, proxy = "http://127.0.0.1:8000", "http://127.0.0.1:5173"
    with httpx.Client(timeout=30, trust_env=False) as client:
        assert client.get(origin + "/health/ready").status_code == 200
        assert client.get(proxy).status_code == 200
        assert client.get(proxy + "/health/ready").status_code == 200
        metadata = client.get(origin + "/api/meta").json()
        assert metadata["generation"] == metadata["embedding"] == "fixture"
        assert client.get(origin + "/api/vehicles").status_code == 401
        assert client.get(proxy + "/api/vehicles").status_code == 200
        identifier = "COMPOSE-" + uuid4().hex[:24]
        run_ids = []
        with SessionLocal.begin() as session:
            original = session.get(VehicleListing, "ILAN-1001")
            session.add(
                VehicleListing(
                    id=identifier,
                    requester_id="demo-requester",
                    title="Synthetic Compose verification",
                    scenario="compose-verification",
                    vehicle_json=original.vehicle_json,
                    description=original.description,
                    photos_json=original.photos_json,
                )
            )
            postgres = session.execute(text("select version()")).scalar_one()

        def review():
            response = client.post(
                origin + "/api/reviews",
                headers=headers,
                json={
                    "listing_id": identifier,
                    "workflow": "listing_review",
                    "request_text": "Synthetic Compose fixture review; prepare a local task.",
                },
            )
            response.raise_for_status()
            result = response.json()
            run_ids.append(UUID(result["id"]))
            assert result["status"] == "awaiting_approval"
            return result["action"]["id"]

        try:
            action_id = review()
            with SessionLocal() as session:
                assert session.scalar(
                    select(func.count()).select_from(ReviewTask)
                    .where(ReviewTask.action_id == UUID(action_id))
                ) == 0
            endpoint = origin + f"/api/actions/{action_id}/approve"
            assert client.post(endpoint, headers=headers).status_code == 403
            barrier = Barrier(8)

            def approve(_):
                with httpx.Client(timeout=30, trust_env=False) as parallel:
                    barrier.wait(timeout=15)
                    response = parallel.post(endpoint, headers=approval)
                    response.raise_for_status()
                    result = response.json()
                    assert result["status"] == "succeeded"
                    return result["result_json"]["task_id"]

            with ThreadPoolExecutor(max_workers=8) as executor:
                task_ids = list(executor.map(approve, range(8)))
            assert len(set(task_ids)) == 1
            with SessionLocal() as session:
                assert session.scalar(
                    select(func.count()).select_from(ReviewTask)
                    .where(ReviewTask.action_id == UUID(action_id))
                ) == 1
                assert session.scalar(
                    select(func.count()).select_from(RunEvent)
                    .where(RunEvent.run_id == run_ids[0], RunEvent.event_type == "tool_executed")
                ) == 1

            rejected = review()
            response = client.post(origin + f"/api/actions/{rejected}/reject", headers=approval)
            assert response.status_code == 200
            assert response.json()["status"] == "rejected"
            assert client.post(
                origin + f"/api/actions/{rejected}/approve", headers=approval
            ).status_code == 409
            proxied = review()
            assert client.post(proxy + f"/api/actions/{proxied}/approve").status_code == 200
            with SessionLocal() as session:
                assert session.scalar(
                    select(func.count()).select_from(ReviewTask)
                    .where(ReviewTask.listing_id == identifier)
                ) == 2
            report = {
                "verified_at": datetime.now(UTC).isoformat(),
                "database": postgres,
                "mode": "fixture; synthetic data; no model-provider calls",
                "checks": {
                    "backend_readiness": True,
                    "nginx_frontend_and_proxy": True,
                    "requester_auth_required": True,
                    "no_task_before_approval": True,
                    "reviewer_auth_required": True,
                    "rejection_cannot_execute": True,
                    "proxy_explicit_approval": True,
                    "parallel_approval_requests": 8,
                    "parallel_unique_tasks": 1,
                    "parallel_execution_audit_events": 1,
                },
                "limits": "Small local concurrency check, not load/scale or identity proof.",
            }
            directory = ROOT / ".local"
            directory.mkdir(exist_ok=True)
            (directory / "compose-verification.json").write_text(
                json.dumps(report, indent=2), encoding="utf-8"
            )
            print(json.dumps(report, indent=2))
        finally:
            with SessionLocal.begin() as session:
                actions = session.scalars(select(Action.id).where(Action.run_id.in_(run_ids))).all()
                session.execute(delete(ReviewTask).where(ReviewTask.action_id.in_(actions)))
                session.execute(delete(Action).where(Action.run_id.in_(run_ids)))
                session.execute(delete(RunEvent).where(RunEvent.run_id.in_(run_ids)))
                session.execute(delete(Run).where(Run.id.in_(run_ids)))
                session.execute(delete(VehicleListing).where(VehicleListing.id == identifier))


if __name__ == "__main__":
    verify()
