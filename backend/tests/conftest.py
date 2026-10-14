import os
from uuid import uuid4

# The test process defaults to fixture mode regardless of a developer's .env.
os.environ["LLM_PROVIDER"] = "fixture"
os.environ["EMBEDDING_PROVIDER"] = "fixture"

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.config import get_settings
from app.db import SessionLocal
from app.main import app
from app.models import Action, ReviewTask, Run, RunEvent


@pytest.fixture(autouse=True)
def block_paid_http(monkeypatch):
    original = httpx.Client.send

    def guarded(client, request, *args, **kwargs):
        if request.url.host not in {"testserver", "localhost", "127.0.0.1"}:
            raise RuntimeError("External HTTP is disabled in automated tests")
        return original(client, request, *args, **kwargs)

    monkeypatch.setattr(httpx.Client, "send", guarded)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def headers():
    return {"X-Demo-Token": get_settings().demo_requester_token.get_secret_value()}


@pytest.fixture
def prefix():
    value = f"pytest-{uuid4()}"
    yield value
    with SessionLocal.begin() as session:
        ids = session.query(Run.id).filter(Run.request_text.startswith(value)).all()
        for (run_id,) in ids:
            action_ids = session.scalars(select(Action.id).where(Action.run_id == run_id)).all()
            for action_id in action_ids:
                session.execute(delete(ReviewTask).where(ReviewTask.action_id == action_id))
                session.execute(delete(Action).where(Action.id == action_id))
            session.execute(delete(RunEvent).where(RunEvent.run_id == run_id))
            session.execute(delete(Run).where(Run.id == run_id))
