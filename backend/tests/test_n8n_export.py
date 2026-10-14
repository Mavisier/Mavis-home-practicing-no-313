import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_public_export_has_no_credentials_or_pinned_payloads():
    workflow = json.loads((ROOT / "n8n/agentic-review-workflow.json").read_text())
    assert workflow["active"] is False
    assert workflow["pinData"] == {}
    assert all("credentials" not in node for node in workflow["nodes"])
    webhooks = [n for n in workflow["nodes"] if n["type"] == "n8n-nodes-base.webhook"]
    assert len(webhooks) == 2
    assert all(n["parameters"]["authentication"] == "headerAuth" for n in webhooks)


def test_initial_review_branch_has_no_path_to_action_execution():
    workflow = json.loads((ROOT / "n8n/agentic-review-workflow.json").read_text())
    visited, pending = set(), ["Review webhook"]
    while pending:
        name = pending.pop()
        if name in visited:
            continue
        visited.add(name)
        for branch in workflow["connections"].get(name, {}).get("main", []):
            pending.extend(edge["node"] for edge in branch)
    assert "Await human decision" in visited
    assert "Apply persisted human decision" not in visited
    assert "Decision webhook" not in visited
