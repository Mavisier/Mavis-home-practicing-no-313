from uuid import UUID, uuid4

import pytest
from sqlalchemy import event, func, select, text
from sqlalchemy.exc import SQLAlchemyError

from app.db import SessionLocal
from app.models import Run, RunEvent


def test_request_and_audit_survive_new_database_session(client, headers, prefix):
    message = f"{prefix} DEMO-1042 için iade talebini değerlendir."
    response = client.post("/api/runs", headers=headers, json={"request_text": f"  {message}  "})
    assert response.status_code == 201
    result = response.json()
    assert result["status"] == "received"
    assert result["intent"] is None
    assert result["final_response_json"] is None
    assert [e["event_type"] for e in result["events"]] == ["request_received"]

    # An independent session proves this was committed, not kept in memory.
    with SessionLocal() as session:
        stored = session.get(Run, UUID(result["id"]))
        assert stored.request_text == message
        assert stored.requester_id == "demo-requester"
    detail = client.get(f"/api/runs/{result['id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json() == result
    listing = client.get("/api/runs", headers=headers)
    assert result["id"] in [item["id"] for item in listing.json()]


@pytest.mark.parametrize("token", [None, "wrong-token"])
def test_requests_require_valid_identity(client, token):
    headers = {} if token is None else {"X-Demo-Token": token}
    assert client.get("/api/runs", headers=headers).status_code == 401
    assert (
        client.post("/api/runs", headers=headers, json={"request_text": "Bir talep"}).status_code
        == 401
    )


@pytest.mark.parametrize(
    "body",
    [
        {"request_text": "   "},
        {"request_text": "ab"},
        {"request_text": "x" * 4001},
        {"request_text": "Bir talep", "requester_id": "admin"},
        {"request_text": "Bir talep", "status": "completed"},
    ],
)
def test_invalid_input_and_identity_spoofing_are_rejected(client, headers, body):
    assert client.post("/api/runs", headers=headers, json=body).status_code == 422


def test_another_requesters_run_is_not_readable(client, headers, prefix):
    with SessionLocal.begin() as session:
        run = Run(requester_id="another-requester", request_text=f"{prefix} özel talep")
        session.add(run)
        session.flush()
        run_id = run.id
    assert client.get(f"/api/runs/{run_id}", headers=headers).status_code == 404
    assert str(run_id) not in [row["id"] for row in client.get("/api/runs", headers=headers).json()]


def test_missing_run_and_invalid_list_limit(client, headers):
    assert client.get(f"/api/runs/{uuid4()}", headers=headers).status_code == 404
    assert client.get("/api/runs?limit=101", headers=headers).status_code == 422


def test_failed_audit_write_rolls_back_request(client, headers, prefix):
    def fail_audit(_mapper, _connection, _target):
        raise SQLAlchemyError("Simulated audit write failure")

    event.listen(RunEvent, "before_insert", fail_audit)
    try:
        response = client.post("/api/runs", headers=headers, json={"request_text": prefix})
        assert response.status_code == 503
        assert response.json() == {"detail": "Database temporarily unavailable"}
    finally:
        event.remove(RunEvent, "before_insert", fail_audit)
    with SessionLocal() as session:
        count = session.scalar(
            select(func.count()).select_from(Run).where(Run.request_text == prefix)
        )
        assert count == 0


def test_readiness_requires_migrated_postgres_and_real_vector_extension(client):
    assert client.get("/health").json()["status"] == "ok"
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["vector_extension"] is True
    with SessionLocal() as session:
        distance = session.scalar(text("SELECT '[1,0,0]'::vector <=> '[1,0,0]'::vector"))
        assert distance == 0
