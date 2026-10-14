"""Import five browser-captured public listing snapshots for local testing.

No login, CAPTCHA solving or private endpoints. The browser captures must exist
first. Only image URLs present in those captures are downloaded.
"""

import hashlib
import html
import json
import re
from io import BytesIO
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from bs4 import BeautifulSoup
from PIL import Image

from app.config import PROJECT_ROOT, get_settings
from app.db import SessionLocal
from app.models import VehicleListing
from app.schemas import ReviewCreate
from app.services.review import process_review

CAPTURE_ROOT = PROJECT_ROOT / "data/real_listings"


def clean_text(value):
    return " ".join(value.split())


def number(value):
    if not value or "belirtilme" in value.casefold():
        return None
    match = re.search(r"\d[\d. ]*", value)
    return int(re.sub(r"\D", "", match.group())) if match else None


def parse_listing(folder: Path):
    capture = json.loads((folder / "capture.json").read_text(encoding="utf-8"))
    source = urlsplit(capture["url"])
    if (
        source.scheme != "https"
        or source.hostname != "www.arabam.com"
        or not source.path.startswith("/ilan/")
    ):
        raise ValueError("Capture must reference a public arabam.com listing")
    raw = (folder / "original.html").read_text(encoding="utf-8")
    if "[Truncated]" in raw or not raw.rstrip().endswith("</html>"):
        raise ValueError("Incomplete browser HTML capture")
    soup = BeautifulSoup(raw, "html.parser")
    properties = {}
    for item in soup.select(".property-item"):
        key, value = item.select_one(".property-key"), item.select_one(".property-value")
        if key and value:
            properties[clean_text(key.get_text())] = clean_text(value.get_text())
    if str(number(properties.get("İlan No"))) != folder.name:
        raise ValueError("Listing ID does not match captured page")
    description_node = soup.select_one("#tab-description > div")
    description = description_node.get_text("\n", strip=True) if description_node else ""
    # Contact data is unnecessary for local model context; raw archive is separate.
    description = re.sub(
        r"(?<!\d)(?:\+?90[ -]*)?0?5\d{2}[ -]*\d{3}[ -]*\d{2}[ -]*\d{2}(?!\d)",
        "[telefon çıkarıldı]",
        description,
    )
    painted, replaced, unspecified = [], [], []
    damage_groups = soup.select("#tab-damage-information .car-damage-info-item")
    for group in damage_groups:
        label = clean_text(group.select_one("p").get_text()).casefold()
        parts = [
            clean_text(li.get_text()) for li in group.select("li") if li.get_text(strip=True) != "-"
        ]
        if "boyal" in label:
            painted.extend(("Lokal: " if "lokal" in label else "") + part for part in parts)
        elif "değiş" in label:
            replaced.extend(parts)
        elif "belirtil" in label:
            unspecified.extend(parts)
    tramer = soup.select_one("#tab-damage-information .tramer-info")
    tramer_text = clean_text(tramer.get_text()) if tramer else None
    price = soup.select_one(".desktop-information-price")
    heading = soup.find("h1")
    title = clean_text(heading.get_text()) if heading else capture["title"].split(" | ")[0]
    # Advert headline is kept separately from the vehicle's model description.
    photos = []
    seen = set()
    for image in capture["images"]:
        url = image["url"]
        parsed = urlsplit(url)
        if (
            parsed.scheme != "https"
            or parsed.hostname != "arbstorage.mncdn.com"
            or parsed.username
            or parsed.password
            or parsed.port not in {None, 443}
            or "/ilanfotograflari/" not in parsed.path
        ):
            continue
        if "/" + folder.name + "/" not in url:
            continue
        key = re.sub(r"_\d+x\d+(?=\.[a-z]+$)", "", urlsplit(url).path)
        if key not in seen:
            seen.add(key)
            photos.append(url)
    # The first main slider image has the original advert headline in its alt.
    headline = next(
        (i["alt"] for i in capture["images"] if "/ilanfotograflari/" in i["url"] and i.get("alt")),
        title,
    )
    km = number(properties.get("Kilometre"))
    year = number(properties.get("Yıl"))
    if km is None or year is None or not description:
        raise ValueError("Required public fields could not be parsed")
    city = re.search(r"Model (.*?) \d[\d. ]* (?:KM|km)", title)
    record = {
        "id": "REAL-" + folder.name,
        "title": title,
        "scenario": "Gerçek ilan · " + folder.name,
        "description": description,
        "photos": [],
        "vehicle": {
            "brand": properties.get("Marka"),
            "model": properties.get("Seri"),
            "year": year,
            "km": km,
            "fuel": properties.get("Yakıt tipi"),
            "gearbox": properties.get("Vites tipi"),
            "price_try": number(price.get_text()) if price else None,
            "painted_parts": painted if damage_groups and not unspecified else None,
            "replaced_parts": replaced,
            "damage_record_try": number(tramer_text),
            "city": city.group(1) if city else "Belirtilmedi",
            "inspection_days_remaining": None,
            "spare_key": None,
            "advert_title": headline,
            "unspecified_parts": unspecified,
            "source": {
                "kind": "public_listing",
                "url": capture["url"],
                "captured_at": capture["captured_at"],
                "listing_id": folder.name,
                "html_sha256": hashlib.sha256(raw.encode()).hexdigest(),
                "photo_angles": "not_classified",
                "photo_resolution_scope": "site_preview",
            },
        },
    }
    return record, photos, properties


def download_images(folder, urls):
    directory = folder / "images"
    directory.mkdir(exist_ok=True)
    images = []
    with httpx.Client(timeout=20, follow_redirects=False) as client:
        for index, url in enumerate(urls, 1):
            response = client.get(url)
            response.raise_for_status()
            if len(response.content) > 15_000_000:
                raise ValueError("Image exceeds local snapshot size limit")
            with Image.open(BytesIO(response.content)) as image:
                width, height = image.size
                image.verify()
                extension = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}.get(image.format)
            if extension is None:
                raise ValueError("Unexpected image format")
            filename = f"photo-{index:03}.{extension}"
            (directory / filename).write_bytes(response.content)
            images.append(
                {
                    "angle": "unknown",
                    "width": width,
                    "height": height,
                    "source_url": url,
                    "url": f"/api/samples/{folder.name}/images/{filename}",
                    "local_file": "images/" + filename,
                    "resolution_scope": "site_preview",
                    "sha256": hashlib.sha256(response.content).hexdigest(),
                }
            )
    return images


def offline_html(record):
    from string import Template

    escape = html.escape

    def display(value):
        if value is None:
            return "Belirtilmemiş"
        if isinstance(value, list):
            return ", ".join(value) if value else "Boya yok (ilan beyanı)"
        return str(value)

    properties = [
        ("Kilometre", record["vehicle"]["km"]),
        ("Yıl", record["vehicle"]["year"]),
        ("Fiyat (ilan beyanı)", record["vehicle"]["price_try"]),
        ("Boya", record["vehicle"]["painted_parts"]),
        ("Hasar tutarı (alan)", record["vehicle"]["damage_record_try"]),
    ]
    cards = "".join(
        f'<figure><img src="{escape(p["local_file"])}" loading="lazy" '
        f'alt="İlan fotoğrafı {i}"><figcaption>Fotoğraf {i} · '
        f"{p['width']} × {p['height']} · site önizlemesi</figcaption></figure>"
        for i, p in enumerate(record["photos"], 1)
    )
    rows = "".join(
        f"<tr><th>{escape(k)}</th><td>{escape(display(v))}</td></tr>" for k, v in properties
    )
    template = Template(
        Path(__file__).with_name("offline_template.html").read_text(encoding="utf-8")
    )
    return template.substitute(
        title=escape(record["title"]),
        source_url=escape(record["vehicle"]["source"]["url"]),
        captured_at=escape(record["vehicle"]["source"]["captured_at"]),
        rows=rows,
        advert_title=escape(record["vehicle"]["advert_title"]),
        description=escape(record["description"]),
        photo_count=len(record["photos"]),
        cards=cards,
    )


def main(reuse_images=False):
    if get_settings().llm_provider != "fixture" or get_settings().embedding_provider != "fixture":
        raise SystemExit(
            "Real listing trials require fixture mode; no remote transmission is enabled."
        )
    report = []
    for folder in sorted(CAPTURE_ROOT.iterdir()):
        if not folder.is_dir() or not folder.name.isdigit():
            continue
        record, urls, properties = parse_listing(folder)
        if reuse_images:
            cached = json.loads((folder / "normalized.json").read_text(encoding="utf-8"))
            if [p["source_url"] for p in cached["photos"]] != urls:
                raise ValueError("Cached images do not match captured page")
            for photo in cached["photos"]:
                path = (folder / photo["local_file"]).resolve()
                path.relative_to((folder / "images").resolve())
                if hashlib.sha256(path.read_bytes()).hexdigest() != photo["sha256"]:
                    raise ValueError("Cached image hash mismatch")
            record["photos"] = cached["photos"]
        else:
            record["photos"] = download_images(folder, urls)
        (folder / "normalized.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (folder / "offline.html").write_text(offline_html(record), encoding="utf-8")
        with SessionLocal.begin() as session:
            row = session.get(VehicleListing, record["id"])
            if row is None:
                row = VehicleListing(id=record["id"], requester_id="demo-requester")
                session.add(row)
            row.title, row.scenario = record["title"], record["scenario"]
            row.vehicle_json, row.description, row.photos_json = (
                record["vehicle"],
                record["description"],
                record["photos"],
            )
        run_id = process_review(
            ReviewCreate(
                listing_id=record["id"],
                workflow="listing_review",
                request_text=record["id"]
                + " gerçek ilan kopyasındaki beyan tutarlılığını kontrol et.",
            ),
            "demo-requester",
        )
        from app.models import Run

        with SessionLocal() as session:
            run = session.get(Run, run_id)
            result = run.final_response_json
            report.append(
                {
                    "id": record["id"],
                    "url": record["vehicle"]["source"]["url"],
                    "photos": len(record["photos"]),
                    "html_complete": True,
                    "run_id": str(run_id),
                    "status": run.status,
                    "findings": result.get("findings", []),
                    "preview_dimensions": sorted(
                        {(p["width"], p["height"]) for p in record["photos"]}
                    ),
                    "claims": "Listing declarations only; no vehicle condition "
                    "verification or vision inference.",
                }
            )
        print(
            json.dumps(
                {
                    "id": record["id"],
                    "photos": len(record["photos"]),
                    "findings": [f["code"] for f in result.get("findings", [])],
                    "status": run.status,
                }
            )
        )
    (CAPTURE_ROOT / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    links = "".join(
        f'<li><a href="{row["id"][5:]}/offline.html">{row["id"]}</a> '
        f"· {row['photos']} fotoğraf</li>"
        for row in report
    )
    (CAPTURE_ROOT / "index.html").write_text(
        '<!doctype html><meta charset="utf-8"><title>Gerçek ilan test kopyaları</title>'
        "<h1>Beş ilan · yerel HTML ve fotoğraflar</h1>"
        "<p>Yalnızca yerel test; araç durumu doğrulanmadı.</p><ul>" + links + "</ul>",
        encoding="utf-8",
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reuse-images", action="store_true", help="Verify cached files without network downloads"
    )
    main(reuse_images=parser.parse_args().reuse_images)
