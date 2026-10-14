"""Diagnostic Turkish rule evaluation: no database, network, embeddings or LLM."""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.vehicle_checks import check_vehicle  # noqa: E402


def evaluate():
    base = {
        "id": "SYNTHETIC-RULE-CASE",
        "description": "",
        "vehicle": {
            "painted_parts": [],
            "replaced_parts": [],
            "damage_record_try": 0,
            "km": 62000,
            "inspection_days_remaining": 90,
            "spare_key": True,
        },
        "photos": [
            {"angle": angle, "width": 1200, "height": 900}
            for angle in ("front", "rear", "side", "interior", "engine")
        ],
    }
    results = []
    for line in (
        (ROOT / "evals/rule_robustness_cases.jsonl").read_text(encoding="utf-8").splitlines()
    ):
        case = json.loads(line)
        record = {
            **base,
            "description": case["description"],
            "vehicle": {**base["vehicle"], **case.get("vehicle", {})},
            "photos": case.get("photos", base["photos"]),
        }
        findings = check_vehicle(record, case.get("workflow", "listing_review"))
        actual = sorted({finding["code"] for finding in findings})
        expected = sorted(case["expected_codes"])
        results.append(
            {
                "id": case["id"],
                "category": case["category"],
                "description": case["description"],
                "expected_codes": expected,
                "actual_codes": actual,
                "matches_expected": actual == expected,
                "label_reason": case["label_reason"],
            }
        )
    mismatches = [row for row in results if not row["matches_expected"]]
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "data": "Hand-authored synthetic Turkish cases; no downloaded listing text.",
        "method": "Expected codes labeled by scenario intent before executing rules.",
        "interpretation": "Diagnostic rule behavior, not real-world accuracy or LLM evaluation.",
        "total": len(results),
        "matching": len(results) - len(mismatches),
        "mismatches": len(mismatches),
        "cases": results,
    }
    directory = ROOT / "evals/reports"
    directory.mkdir(exist_ok=True)
    (directory / "rule-robustness.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Rule diagnostic: {report['matching']}/{report['total']} match expected labels.")
    print(f"Documented deviations: {report['mismatches']}. No model/network calls.")
    for row in mismatches:
        print(f"{row['id']}: expected {row['expected_codes']}; actual {row['actual_codes']}")
    # Mismatches are the useful diagnostic output, not a claim that a CI check passed.
    return report


if __name__ == "__main__":
    evaluate()
