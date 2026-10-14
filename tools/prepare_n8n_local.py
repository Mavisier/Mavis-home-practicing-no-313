"""Bind native header-auth credentials to an ignored LOCAL copy of the export."""

import json
import subprocess

from integration_env import ROOT, environment, n8n_command


def prepare():
    env = environment()
    folder = ROOT / ".local/integrations"
    credentials = []
    for name, key in [
        ("Review", "N8N_REVIEW_WEBHOOK_TOKEN"),
        ("Decision", "N8N_DECISION_WEBHOOK_TOKEN"),
    ]:
        credentials.append(
            {
                "id": "agenticLocal" + name,
                "name": "Local " + name + " webhook",
                "type": "httpHeaderAuth",
                "data": {"name": "X-Workflow-Key", "value": env[key]},
            }
        )
    path = folder / "credentials.json"
    path.write_text(json.dumps(credentials), encoding="utf-8")
    workflow = json.loads((ROOT / "n8n/agentic-review-workflow.json").read_text())
    for node in workflow["nodes"]:
        if node["name"] in {"Review webhook", "Decision webhook"}:
            suffix = node["name"].split()[0]
            node["credentials"] = {
                "httpHeaderAuth": {
                    "id": "agenticLocal" + suffix,
                    "name": "Local " + suffix + " webhook",
                }
            }
    local_path = folder / "workflow-local.json"
    local_path.write_text(json.dumps(workflow), encoding="utf-8")
    for args in [
        ("import:credentials", "--input=" + str(path)),
        ("import:workflow", "--input=" + str(local_path)),
        ("publish:workflow", "--id=agenticReviewPortfolio"),
    ]:
        subprocess.run(n8n_command(*args), env=env, check=True)
    print("Local credentials bound; the public export remains credential-free.")


if __name__ == "__main__":
    prepare()
