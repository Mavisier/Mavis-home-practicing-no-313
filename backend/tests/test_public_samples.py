import json

from app.services.vehicle_checks import check_vehicle
from scripts.import_real_listings import offline_html, parse_listing


def listing(description="Boyasız değil; sol kapı boyalıdır."):
    return {
        "id": "test",
        "description": description,
        "vehicle": {
            "painted_parts": ["Sol kapı"],
            "damage_record_try": 0,
            "replaced_parts": [],
            "km": 104000,
            "advert_title": "2014 MODEL 99.000 KM",
            "source": {"photo_angles": "not_classified"},
        },
        "photos": [
            {"angle": "unknown", "width": 580, "height": 435, "resolution_scope": "site_preview"}
        ],
    }


def test_site_preview_is_not_misreported_as_poor_photo_or_missing_angle():
    codes = {f["code"] for f in check_vehicle(listing(), "listing_review")}
    assert "photo_resolution" not in codes
    assert "photo_coverage" not in codes
    assert "paint_contradiction" not in codes
    assert "title_km_mismatch" in codes


def test_damage_in_description_is_not_filled_in_as_verified_form_value():
    record = listing("Far değişiminden 35 bin TL yeni tarihli hasar kaydı vardır.")
    record["vehicle"]["damage_record_try"] = None
    findings = check_vehicle(record, "listing_review")
    assert "damage_record_in_description" in {f["code"] for f in findings}
    assert record["vehicle"]["damage_record_try"] is None


def test_explicit_paintless_claim_with_painted_field_is_flagged():
    codes = {f["code"] for f in check_vehicle(listing("BOYASIZ DEĞİŞENSİZ"), "listing_review")}
    assert "paint_contradiction" in codes


def test_copy_button_text_does_not_break_listing_id_parser(tmp_path):
    # Invented identifier for a synthetic parser fixture; not a captured listing ID.
    folder = tmp_path / "90000001"
    folder.mkdir()
    document = """<!doctype html><html><h1>Toyota 2014 Model İstanbul 104.000 KM</h1>
      <div class="property-item"><div class="property-key">İlan No</div>
      <div class="property-value">Kopyalandı 90000001</div></div>
      <div class="property-item"><div class="property-key">Yıl</div>
      <div class="property-value">2014</div></div>
      <div class="property-item"><div class="property-key">Kilometre</div>
      <div class="property-value">104.000 KM</div></div>
      <div id="tab-description"><div>Araç bakımlıdır.</div></div></html>"""
    (folder / "original.html").write_text(document, encoding="utf-8")
    (folder / "capture.json").write_text(
        json.dumps(
            {
                "title": "Toyota",
                "url": "https://www.arabam.com/ilan/example/90000001",
                "captured_at": "2026-10-13T00:00:00Z",
                "images": [],
            }
        ),
        encoding="utf-8",
    )
    record, _, _ = parse_listing(folder)
    assert record["vehicle"]["km"] == 104000
    assert record["vehicle"]["painted_parts"] is None
    assert record["vehicle"]["damage_record_try"] is None


def test_offline_html_escapes_untrusted_seller_markup():
    record = {
        "title": "Test",
        "vehicle": {
            "km": 100,
            "year": 2020,
            "price_try": None,
            "painted_parts": None,
            "damage_record_try": None,
            "advert_title": "Örnek",
            "source": {"url": "https://www.arabam.com/", "captured_at": "2026-10-13"},
        },
        "description": "<script>malicious()</script>",
        "photos": [],
    }
    rendered = offline_html(record)
    assert "<script>" not in rendered
    assert "&lt;script&gt;" in rendered
    assert "Content-Security-Policy" in rendered
