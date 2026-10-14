from uuid import uuid4

import pytest

from app.api import reviews
from app.db import SessionLocal
from app.models import VehicleListing


@pytest.fixture
def local_sample(tmp_path, monkeypatch):
    listing_id = str(20000000 + uuid4().int % 10000000)
    folder = tmp_path / "data/real_listings" / listing_id
    (folder / "images").mkdir(parents=True)
    # FileResponse routing test; image decoding is tested during import.
    (folder / "images/photo-001.jpg").write_bytes(b"test-jpeg-body")
    (folder / "offline.html").write_text("<!doctype html><title>Local snapshot</title>")
    monkeypatch.setattr(reviews, "PROJECT_ROOT", tmp_path)
    with SessionLocal.begin() as session:
        session.add(
            VehicleListing(
                id="REAL-" + listing_id,
                requester_id="demo-requester",
                title="Test sample",
                scenario="test",
                description="Test description",
                vehicle_json={},
                photos_json=[],
            )
        )
    yield listing_id
    with SessionLocal.begin() as session:
        session.delete(session.get(VehicleListing, "REAL-" + listing_id))


def test_sample_images_require_identity(client, headers, local_sample):
    url = f"/api/samples/{local_sample}/images/photo-001.jpg"
    assert client.get(url).status_code == 401
    response = client.get(url, headers=headers)
    assert response.status_code == 200
    assert response.content == b"test-jpeg-body"
    assert response.headers["content-type"] == "image/jpeg"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_raw_capture_and_arbitrary_filenames_cannot_be_served(client, headers, local_sample):
    for filename in ["original.html", "capture.json", "photo-001.jpg.bak"]:
        response = client.get(f"/api/samples/{local_sample}/images/{filename}", headers=headers)
        assert response.status_code == 404


def test_offline_snapshot_has_no_script_execution_permission(client, headers, local_sample):
    response = client.get(f"/api/samples/{local_sample}/offline", headers=headers)
    assert response.status_code == 200
    assert "script-src 'none'" in response.headers["content-security-policy"]
    assert "default-src 'none'" in response.headers["content-security-policy"]
