import json
from datetime import datetime, timedelta, timezone

from sqlalchemy.dialects.postgresql import insert

from app.config import PROJECT_ROOT
from app.db import SessionLocal
from app.models import Order, SupportTicket, VehicleListing
from app.services.knowledge import ingest


def seed():
    now = datetime.now(timezone.utc)
    orders = [
        {
            "id": "DEMO-1042",
            "requester_id": "demo-requester",
            "amount_minor": 149900,
            "currency": "TRY",
            "paid_at": now - timedelta(days=2),
            "service_used": False,
        },
        {
            "id": "DEMO-1043",
            "requester_id": "demo-requester",
            "amount_minor": 89900,
            "currency": "TRY",
            "paid_at": now - timedelta(days=3),
            "service_used": True,
        },
        {
            "id": "DEMO-OTHER",
            "requester_id": "another-requester",
            "amount_minor": 49900,
            "currency": "TRY",
            "paid_at": now - timedelta(days=1),
            "service_used": False,
        },
    ]
    with SessionLocal.begin() as session:
        session.execute(insert(Order).values(orders).on_conflict_do_nothing(index_elements=["id"]))
        session.execute(
            insert(SupportTicket)
            .values(
                id="TICKET-2001",
                requester_id="demo-requester",
                subject="İlan hizmeti erişim sorunu",
                priority="normal",
                status="open",
            )
            .on_conflict_do_nothing(index_elements=["id"])
        )
    records = json.loads(
        (PROJECT_ROOT / "data/fixtures/vehicle_listings.json").read_text(encoding="utf-8")
    )
    with SessionLocal.begin() as session:
        for record in records:
            session.execute(
                insert(VehicleListing)
                .values(
                    id=record["id"],
                    requester_id="demo-requester",
                    title=record["title"],
                    scenario=record["scenario"],
                    vehicle_json=record["vehicle"],
                    description=record["description"],
                    photos_json=record["photos"],
                )
                .on_conflict_do_nothing(index_elements=["id"])
            )
    count = ingest()
    print(f"Synthetic seed ready; {count} knowledge documents indexed.")


if __name__ == "__main__":
    seed()
