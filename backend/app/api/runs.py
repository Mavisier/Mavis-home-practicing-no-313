from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_requester
from app.db import get_session
from app.models import Action, Run, RunEvent
from app.schemas import ActionRead, EventRead, RunCreate, RunRead, RunSummary

router = APIRouter(prefix="/api/runs", tags=["runs"])
DbSession = Annotated[Session, Depends(get_session)]
Requester = Annotated[str, Depends(get_requester)]


def read_run(session: Session, run: Run) -> RunRead:
    events = session.scalars(
        select(RunEvent).where(RunEvent.run_id == run.id).order_by(RunEvent.sequence)
    ).all()
    action = session.scalar(select(Action).where(Action.run_id == run.id))
    return RunRead(
        **RunSummary.model_validate(run).model_dump(),
        final_response_json=run.final_response_json,
        events=[EventRead.model_validate(event) for event in events],
        action=ActionRead.model_validate(action) if action else None,
    )


@router.post("", response_model=RunRead, status_code=201)
def create_run(body: RunCreate, session: DbSession, requester: Requester) -> RunRead:
    run = Run(requester_id=requester, request_text=body.request_text)
    # One transaction: a request must never exist without its initial audit event.
    with session.begin():
        session.add(run)
        session.flush()
        session.add(
            RunEvent(
                run_id=run.id,
                sequence=1,
                event_type="request_received",
                payload_json={"message": "Talep kaydedildi.", "milestone": 1},
            )
        )
    return read_run(session, run)


@router.get("", response_model=list[RunSummary])
def list_runs(
    session: DbSession,
    requester: Requester,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[Run]:
    return list(
        session.scalars(
            select(Run)
            .where(Run.requester_id == requester)
            .order_by(Run.started_at.desc(), Run.id.desc())
            .limit(limit)
        )
    )


@router.get("/{run_id}", response_model=RunRead)
def get_run(run_id: UUID, session: DbSession, requester: Requester) -> RunRead:
    run = session.scalar(select(Run).where(Run.id == run_id, Run.requester_id == requester))
    if run is None:
        raise HTTPException(status_code=404, detail="Request not found")
    return read_run(session, run)
