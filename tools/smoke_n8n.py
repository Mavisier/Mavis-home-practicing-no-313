"""Exercise the local workflow with fixture records; never print auth values."""

import json
from datetime import UTC, datetime

import httpx

from integration_env import ROOT, environment


def main():
    env = environment()
    review_url = "http://127.0.0.1:5678/webhook/agentic-review"
    decision_url = "http://127.0.0.1:5678/webhook/agentic-review-decision"
    headers = {"X-Workflow-Key": env["N8N_REVIEW_WEBHOOK_TOKEN"]}
    decision_headers = {"X-Workflow-Key": env["N8N_DECISION_WEBHOOK_TOKEN"]}
    api_headers = {"X-Demo-Token": env["ASSISTANT_DEMO_REQUESTER_TOKEN"]}
    with httpx.Client(timeout=60) as client:
        payload = {
            "listing_id": "ILAN-1001",
            "workflow": "listing_review",
            "request_text": "n8n fixture demo: check declarations and propose a review.",
        }
        assert client.post(review_url, json=payload).status_code == 403
        assert (
            client.post(review_url, headers=headers, json={**payload, "approve": True}).status_code
            == 400
        )
        result = client.post(review_url, headers=headers, json=payload)
        result.raise_for_status()
        pending = result.json()
        assert pending["status"] == "awaiting_approval" and pending["requires_approval"] is True
        run = client.get(
            env["ASSISTANT_BASE_URL"] + "/api/runs/" + pending["run_id"], headers=api_headers
        ).json()
        assert (
            run["action"]["status"] == "pending_approval" and run["action"]["result_json"] is None
        )
        decision = {"action_id": pending["action_id"], "decision": "approve"}
        assert client.post(decision_url, headers=headers, json=decision).status_code == 403
        approved = client.post(decision_url, headers=decision_headers, json=decision)
        approved.raise_for_status()
        first = approved.json()
        assert first["status"] == "succeeded"
        again = client.post(decision_url, headers=decision_headers, json=decision)
        again.raise_for_status()
        assert again.json()["result"] == first["result"]
        clean = client.post(
            review_url, headers=headers, json={**payload, "listing_id": "ILAN-1003"}
        )
        clean.raise_for_status()
        assert clean.json()["status"] == "answered" and clean.json()["requires_approval"] is False
        rejection = client.post(review_url, headers=headers, json=payload).json()
        rejected = client.post(
            decision_url,
            headers=decision_headers,
            json={"action_id": rejection["action_id"], "decision": "reject"},
        )
        rejected.raise_for_status()
        assert rejected.json()["status"] == "rejected"
    report = {
        "verified_at": datetime.now(UTC).isoformat(),
        "n8n_version": "2.42.7",
        "mode": "fixture",
        "checks": {
            "unauthorized_rejected": True,
            "invalid_input_rejected": True,
            "approval_not_automatic": True,
            "separate_decision_authority": True,
            "approved_task_persisted": True,
            "repeat_approval_idempotent": True,
            "consistent_record_no_action": True,
            "rejection_persisted": True,
        },
    }
    path = ROOT / "docs/verification/n8n.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("n8n local fixture workflow: 8 checks passed; no credentials printed.")


if __name__ == "__main__":
    main()
