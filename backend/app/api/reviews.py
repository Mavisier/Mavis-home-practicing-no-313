import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.runs import read_run
from app.auth import get_approver, get_requester
from app.config import PROJECT_ROOT
from app.db import get_session
from app.models import Action, ReviewTask, Run, VehicleListing
from app.schemas import ActionRead, DescriptionEdit, ReviewCreate, RunRead
from app.services.review import append_event, listing_dict, payload_hash, process_review

router = APIRouter(prefix="/api", tags=["vehicle operations"])
DbSession = Annotated[Session, Depends(get_session)]
Requester = Annotated[str, Depends(get_requester)]
Approver = Annotated[str, Depends(get_approver)]


def sample_folder(listing_id: str, session: Session, requester: str) -> Path:
    if not re.fullmatch(r"\d{6,12}", listing_id):
        raise HTTPException(404, "Sample not found")
    row = session.scalar(
        select(VehicleListing).where(
            VehicleListing.id == "REAL-" + listing_id, VehicleListing.requester_id == requester
        )
    )
    if row is None:
        raise HTTPException(404, "Sample not found")
    root = (PROJECT_ROOT / "data/real_listings").resolve()
    folder = (root / listing_id).resolve()
    try:
        folder.relative_to(root)
    except ValueError:
        raise HTTPException(404, "Sample not found") from None
    return folder


@router.get("/samples/{listing_id}/images/{filename}")
def sample_image(listing_id: str, filename: str, session: DbSession, requester: Requester):
    if not re.fullmatch(r"photo-\d{3}\.(jpg|png|webp)", filename):
        raise HTTPException(404, "Image not found")
    folder = sample_folder(listing_id, session, requester)
    path = (folder / "images" / filename).resolve()
    try:
        path.relative_to(folder)
    except ValueError:
        raise HTTPException(404, "Image not found") from None
    if not path.is_file():
        raise HTTPException(404, "Image not found")
    types = {".jpg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    return FileResponse(
        path, media_type=types[path.suffix], headers={"X-Content-Type-Options": "nosniff"}
    )


@router.get("/samples/{listing_id}/offline")
def sample_html(listing_id: str, session: DbSession, requester: Requester):
    folder = sample_folder(listing_id, session, requester)
    path = (folder / "offline.html").resolve()
    try:
        path.relative_to(folder)
    except ValueError:
        raise HTTPException(404, "Snapshot not found") from None
    if not path.is_file():
        raise HTTPException(404, "Snapshot not found")
    return FileResponse(
        path,
        media_type="text/html",
        headers={
            "Content-Security-Policy": "default-src 'none'; img-src 'self'; "
            "style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; script-src 'none'",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/vehicles")
def vehicles(session: DbSession, requester: Requester):
    rows = session.scalars(
        select(VehicleListing)
        .where(VehicleListing.requester_id == requester)
        .order_by(VehicleListing.id)
    )
    return [listing_dict(row) for row in rows]


@router.patch("/vehicles/{listing_id}")
def edit_description(
    listing_id: str, body: DescriptionEdit, session: DbSession, requester: Requester
):
    with session.begin():
        row = session.scalar(
            select(VehicleListing)
            .where(VehicleListing.id == listing_id, VehicleListing.requester_id == requester)
            .with_for_update()
        )
        if row is None:
            raise HTTPException(404, "Vehicle record not found")
        row.description = body.description
    return listing_dict(row)


@router.post("/reviews", response_model=RunRead, status_code=201)
def review(body: ReviewCreate, session: DbSession, requester: Requester):
    run_id = process_review(body, requester)
    return read_run(session, session.get(Run, run_id))


@router.get("/review-tasks")
def tasks(session: DbSession, requester: Requester):
    records = session.scalars(
        select(ReviewTask)
        .join(VehicleListing)
        .where(VehicleListing.requester_id == requester)
        .order_by(ReviewTask.created_at.desc())
        .limit(50)
    )
    return [
        {
            "id": str(row.id),
            "listing_id": row.listing_id,
            "status": row.status,
            "created_at": row.created_at,
            "payload": row.payload_json,
        }
        for row in records
    ]


@router.post("/actions/{action_id}/{decision}", response_model=ActionRead)
def decide(
    action_id: UUID, decision: str, session: DbSession, requester: Requester, approver: Approver
):
    if decision not in {"approve", "reject"}:
        raise HTTPException(404, "Unknown decision")
    with session.begin():
        action = session.scalar(select(Action).where(Action.id == action_id).with_for_update())
        if action is None:
            raise HTTPException(404, "Action not found")
        run = session.scalar(
            select(Run)
            .where(Run.id == action.run_id, Run.requester_id == requester)
            .with_for_update()
        )
        if run is None:
            raise HTTPException(404, "Action not found")
        if action.status == "succeeded" and decision == "approve":
            return ActionRead.model_validate(action)
        if action.status != "pending_approval":
            raise HTTPException(409, "Action is no longer awaiting approval")
        if decision == "reject":
            action.status = "rejected"
            run.status = "rejected"
            append_event(
                session,
                run.id,
                "action_rejected",
                {"message": "İnceleme görevi reddedildi; uygulanmadı."},
            )
        else:
            if (
                action.tool_name != "create_review_task"
                or payload_hash(action.arguments_json) != action.payload_hash
            ):
                raise HTTPException(409, "Approval payload no longer valid")
            row = session.scalar(
                select(VehicleListing)
                .where(
                    VehicleListing.id == action.arguments_json["listing_id"],
                    VehicleListing.requester_id == requester,
                )
                .with_for_update()
            )
            if (
                row is None
                or payload_hash(listing_dict(row)) != action.arguments_json["listing_snapshot_hash"]
            ):
                raise HTTPException(
                    409, "Vehicle record changed. Run a new review before approving."
                )
            task = ReviewTask(
                action_id=action.id, listing_id=row.id, payload_json=action.arguments_json
            )
            session.add(task)
            session.flush()
            action.status = "succeeded"
            action.approved_by = approver
            action.approved_at = datetime.now(timezone.utc)
            action.result_json = {"task_id": str(task.id), "listing_id": row.id, "local_only": True}
            run.status = "completed"
            append_event(
                session,
                run.id,
                "action_approved",
                {"message": "Demo inceleyici sabitlenmiş içeriği onayladı.", "actor": approver},
            )
            append_event(
                session,
                run.id,
                "tool_executed",
                {
                    "tool": action.tool_name,
                    "message": "Yerel operasyon görevi oluşturuldu.",
                    "result": action.result_json,
                },
            )
    return ActionRead.model_validate(action)
