import re
import unicodedata


def normalized(value: str) -> str:
    lowered = value.casefold().replace("ı", "i")
    return "".join(c for c in unicodedata.normalize("NFD", lowered) if not unicodedata.combining(c))


def damage_amount_mentioned(description: str) -> bool:
    text = normalized(description)
    for match in re.finditer(r"\b\d[\d.]*\s*(?:bin\s*)?(?:tl|₺)\b", text):
        window = text[max(0, match.start() - 70) : match.end() + 70]
        if "hasar" in window or "tramer" in window:
            return True
    return False


def check_vehicle(listing: dict, workflow: str) -> list[dict]:
    vehicle = listing["vehicle"]
    findings = []

    def add(code, severity, title, detail, question, source):
        findings.append(
            {
                "code": code,
                "severity": severity,
                "title": title,
                "detail": detail,
                "question": question,
                "source_id": source,
            }
        )

    for field, label in [("painted_parts", "Boyalı parça"), ("damage_record_try", "Hasar kaydı")]:
        if (
            field == "damage_record_try"
            and vehicle.get(field) is None
            and damage_amount_mentioned(listing["description"])
        ):
            add(
                "damage_record_in_description",
                "high",
                "Hasar tutarı açıklamada; Tramer alanı boş",
                "Açıklamada hasar/Tramer tutarı ifadesi bulunuyor; "
                "yapılandırılmış alanda tutar belirtilmemiş.",
                "Açıklamadaki hasar tutarını teyit edip Tramer alanına da ekleyebilir misiniz?",
                "listing-information" if workflow == "listing_review" else "trink-preparation",
            )
        elif vehicle.get(field) is None:
            add(
                f"missing_{field}",
                "high",
                f"{label} bilgisi eksik",
                "Boş bırakılan alan, olmadığı anlamına gelmez.",
                f"{label} bilginizi teyit edip ilgili alanı doldurabilir misiniz?",
                "listing-information" if workflow == "listing_review" else "trink-preparation",
            )

    if workflow == "listing_review":
        description = normalized(listing["description"])
        if vehicle.get("painted_parts") and re.search(
            r"\bboyasiz(?:dir)?\b(?!\s+(?:degil|gocuk))", description
        ):
            parts = ", ".join(vehicle["painted_parts"])
            add(
                "paint_contradiction",
                "high",
                "Boya beyanı ile açıklama çelişiyor",
                f"Formda {parts} boyalı; açıklamada 'boyasız' ifadesi var.",
                f"{parts} için boya beyanını teyit edip açıklamadaki "
                "boyasız ifadesini düzeltebilir misiniz?",
                "listing-information",
            )
        if vehicle.get("replaced_parts") and re.search(
            r"\bdegisensiz(?:dir)?\b(?!\s+degil)|"
            r"\bdegisen(?:\s+parca)?\s+yok(?:tur)?\b(?!\s+degil)",
            description,
        ):
            add(
                "replacement_contradiction",
                "high",
                "Değişen parça beyanı çelişiyor",
                "Formdaki değişen parça bilgisi açıklamayla örtüşmüyor.",
                "Değişen parça bilgilerini teyit eder misiniz?",
                "listing-information",
            )
        if vehicle.get("damage_record_try", 0) and re.search(
            r"\bhasar kaydi yok(?:tur)?\b(?!\s+degil)|"
            r"\bhasarsiz(?:dir)?\b(?!\s+degil)",
            description,
        ):
            add(
                "damage_contradiction",
                "high",
                "Hasar kaydı beyanı çelişiyor",
                "Formda hasar tutarı bulunuyor; açıklama hasar olmadığını belirtiyor.",
                "Hasar kaydı tutarını ve açıklamayı teyit eder misiniz?",
                "listing-information",
            )
        headline = vehicle.get("advert_title", "")
        declared_km = vehicle.get("km")
        for match in re.finditer(r"\b(\d[\d., ]{1,12})\s*(?:km|kilometre)\b", normalized(headline)):
            title_km = int(re.sub(r"\D", "", match.group(1)))
            if declared_km is not None and title_km != declared_km:
                add(
                    "title_km_mismatch",
                    "high",
                    "Başlık ve kilometre alanı farklı",
                    "İlan başlığında "
                    + f"{title_km:,}".replace(",", ".")
                    + " km; kilometre alanında "
                    + f"{declared_km:,}".replace(",", ".")
                    + " km var. "
                    "Başlık eski kalmış olabilir; bu tespit km müdahalesi kanıtı değildir.",
                    "Güncel kilometreyi teyit edip başlık ve kilometre "
                    "alanını eşitleyebilir misiniz?",
                    "listing-information",
                )
                break
        angles = {photo["angle"] for photo in listing["photos"]}
        labels = {"front": "ön", "rear": "arka", "side": "yan", "interior": "iç", "engine": "motor"}
        missing = [labels[angle] for angle in labels if angle not in angles]
        if missing and vehicle.get("source", {}).get("photo_angles") != "not_classified":
            add(
                "photo_coverage",
                "medium",
                "Fotoğraf kapsamı geliştirilebilir",
                f"Fotoğraf metadata'sında eksik açılar: {', '.join(missing)}.",
                f"Şu açılar için fotoğraf ekleyebilir misiniz: {', '.join(missing)}?",
                "photo-guidance",
            )
        if any(
            max(p["width"], p["height"]) < 800 and p.get("resolution_scope") != "site_preview"
            for p in listing["photos"]
        ):
            add(
                "photo_resolution",
                "medium",
                "Düşük çözünürlük işareti",
                "Demo metadata'sındaki bazı görseller 800 piksel önerisinin altında.",
                "Daha yüksek çözünürlüklü güncel fotoğraflar ekleyebilir misiniz?",
                "photo-guidance",
            )
    else:
        days = vehicle.get("inspection_days_remaining")
        if days is None or days < 30:
            add(
                "inspection_preparation",
                "high",
                "Muayene geçerliliğini teyit edin",
                f"Beyan edilen muayene süresi: {days if days is not None else 'bilinmiyor'} gün. "
                "Herkese açık hazırlık bilgisinde en az 30 gün belirtiliyor.",
                "Randevu öncesinde muayene geçerliliğini kontrol eder misiniz?",
                "trink-preparation",
            )
        if vehicle.get("spare_key") is not True:
            add(
                "spare_key",
                "medium",
                "Yedek anahtar durumunu bildirin",
                "Eksik anahtarın fiyatı etkileyebileceği belirtiliyor; demo fiyat hesaplamaz.",
                "Yedek anahtarın bulunup bulunmadığını teyit eder misiniz?",
                "trink-preparation",
            )
    return findings
