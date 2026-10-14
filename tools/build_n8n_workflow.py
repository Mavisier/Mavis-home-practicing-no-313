"""Generate a credential-free, local orchestration workflow with two entry points."""

import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

ROOT = Path(__file__).resolve().parents[1]
nodes = []
connections = {}


def node(name, kind, parameters, x, y, version=1):
    value = {
        "id": str(uuid5(NAMESPACE_URL, name)),
        "name": name,
        "type": "n8n-nodes-base." + kind,
        "typeVersion": version,
        "position": [x, y],
        "parameters": parameters,
    }
    if kind == "webhook":
        value["webhookId"] = str(uuid5(NAMESPACE_URL, name + "webhook"))
    nodes.append(value)


def link(source, target, branch=0):
    outputs = connections.setdefault(source, {"main": []})["main"]
    while len(outputs) <= branch:
        outputs.append([])
    outputs[branch].append({"node": target, "type": "main", "index": 0})


def condition(expression):
    return {
        "conditions": {
            "options": {"caseSensitive": True, "typeValidation": "strict", "version": 2},
            "conditions": [
                {
                    "id": str(uuid5(NAMESPACE_URL, expression)),
                    "leftValue": "={{ " + expression + " }}",
                    "rightValue": True,
                    "operator": {"type": "boolean", "operation": "true", "singleValue": True},
                }
            ],
            "combinator": "and",
        },
        "options": {},
    }


def respond(name, body, x, y, code=200):
    node(
        name,
        "respondToWebhook",
        {"respondWith": "json", "responseBody": body, "options": {"responseCode": code}},
        x,
        y,
        1.4,
    )


for suffix, path, y in [
    ("Review", "agentic-review", 0),
    ("Decision", "agentic-review-decision", 500),
]:
    node(
        suffix + " webhook",
        "webhook",
        {
            "httpMethod": "POST",
            "path": path,
            "responseMode": "responseNode",
            "authentication": "headerAuth",
            "options": {},
        },
        0,
        y,
        2.1,
    )

review_valid = (
    "$json.body && typeof $json.body.request_text === 'string' && "
    "$json.body.request_text.trim().length >= 3 && $json.body.request_text.length <= 4000 && "
    "typeof $json.body.listing_id === 'string' && "
    "/^[A-Za-z0-9_-]{1,40}$/.test($json.body.listing_id) && "
    "['listing_review','trink_readiness'].includes($json.body.workflow) && "
    "Object.keys($json.body).every(key => ['request_text','listing_id','workflow'].includes(key))"
)
node("Review input valid", "if", condition(review_valid), 470, -40, 2.2)
respond(
    "Invalid review",
    '{"error":"Expected listing_id, workflow and bounded request_text"}',
    700,
    160,
    400,
)
link("Review webhook", "Review input valid")
link("Review input valid", "Invalid review", 1)
node(
    "Call FastAPI review",
    "httpRequest",
    {
        "method": "POST",
        "url": "={{ $env.ASSISTANT_BASE_URL + '/api/reviews' }}",
        "sendHeaders": True,
        "headerParameters": {
            "parameters": [
                {"name": "X-Demo-Token", "value": "={{ $env.ASSISTANT_DEMO_REQUESTER_TOKEN }}"}
            ]
        },
        "sendBody": True,
        "specifyBody": "json",
        "jsonBody": "={{ JSON.stringify($json.body) }}",
        "options": {"timeout": 55000},
    },
    720,
    -40,
    4.3,
)
link("Review input valid", "Call FastAPI review")
node(
    "Human approval required",
    "if",
    condition("Boolean($json.action && $json.action.status === 'pending_approval')"),
    960,
    -40,
    2.2,
)
link("Call FastAPI review", "Human approval required")
respond(
    "Await human decision",
    "={{ JSON.stringify({run_id:$json.id,status:$json.status,requires_approval:true,"
    "action_id:$json.action.id,review:$json.final_response_json,"
    "decision_path:'/webhook/agentic-review-decision'}) }}",
    1190,
    -100,
)
respond(
    "Return completed review",
    "={{ JSON.stringify({run_id:$json.id,status:$json.status,requires_approval:false,"
    "review:$json.final_response_json}) }}",
    1190,
    100,
)
link("Human approval required", "Await human decision")
link("Human approval required", "Return completed review", 1)

decision_valid = (
    "$json.body && typeof $json.body.action_id === 'string' && "
    "/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-"
    "[0-9a-f]{12}$/i.test($json.body.action_id) && "
    "['approve','reject'].includes($json.body.decision) && "
    "Object.keys($json.body).every(key => ['action_id','decision'].includes(key))"
)
node("Human decision valid", "if", condition(decision_valid), 470, 470, 2.2)
respond(
    "Invalid decision",
    '{"error":"Expected action_id UUID and explicit approve or reject"}',
    700,
    670,
    400,
)
link("Decision webhook", "Human decision valid")
link("Human decision valid", "Invalid decision", 1)
node(
    "Apply persisted human decision",
    "httpRequest",
    {
        "method": "POST",
        "url": "={{ $env.ASSISTANT_BASE_URL + '/api/actions/' + "
        "$json.body.action_id + '/' + $json.body.decision }}",
        "sendHeaders": True,
        "headerParameters": {
            "parameters": [
                {"name": "X-Demo-Token", "value": "={{ $env.ASSISTANT_DEMO_REQUESTER_TOKEN }}"},
                {
                    "name": "X-Demo-Approver-Token",
                    "value": "={{ $env.ASSISTANT_DEMO_APPROVER_TOKEN }}",
                },
            ]
        },
        "options": {"timeout": 15000},
    },
    720,
    470,
    4.3,
)
link("Human decision valid", "Apply persisted human decision")
respond(
    "Return persisted final status",
    "={{ JSON.stringify({action_id:$json.id,status:$json.status,result:$json.result_json}) }}",
    960,
    470,
)
link("Apply persisted human decision", "Return persisted final status")

workflow = {
    "id": "agenticReviewPortfolio",
    "name": "Agentic vehicle review with explicit human decision",
    "active": False,
    "nodes": nodes,
    "connections": connections,
    "settings": {
        "executionOrder": "v1",
        "saveDataErrorExecution": "none",
        "saveDataSuccessExecution": "none",
        "saveManualExecutions": False,
        "saveExecutionProgress": False,
    },
    "pinData": {},
    "tags": [],
}
# Native credentials are assigned to the ignored local import, never this export.
target = ROOT / "n8n/agentic-review-workflow.json"
target.parent.mkdir(exist_ok=True)
target.write_text(json.dumps(workflow, indent=2), encoding="utf-8")
print(f"Generated credential-free workflow: {len(workflow['nodes'])} nodes")
