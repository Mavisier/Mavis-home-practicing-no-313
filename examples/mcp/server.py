"""Two read-only stdio MCP tools. No approval, SQL, shell or arbitrary URL tool."""

import os
import sys
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.config import get_settings  # noqa: E402

mcp = FastMCP("Agentic Workflow Assistant read-only demo", log_level="WARNING")


def base_url():
    value = os.getenv("ASSISTANT_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    parsed = urlsplit(value)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "localhost", "backend"}
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path
    ):
        raise ValueError("MCP demo base URL must be an explicit local backend origin")
    return value


def read_run(run_id: str):
    identifier = str(UUID(run_id))
    token = get_settings().demo_requester_token.get_secret_value()
    try:
        with httpx.Client(timeout=10, follow_redirects=False) as client:
            response = client.get(
                base_url() + "/api/runs/" + identifier, headers={"X-Demo-Token": token}
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError:
        raise ValueError("Run could not be read from the local backend") from None


@mcp.tool(
    annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)
)
def get_listing_analysis(run_id: str) -> dict:
    """Read one persisted review's findings and evidence, scoped by backend identity."""
    run = read_run(run_id)
    result = run.get("final_response_json") or {}
    return {
        "run_id": run["id"],
        "status": run["status"],
        "mode": result.get("mode"),
        "explanation_kind": result.get("explanation_kind"),
        "verdict": result.get("verdict"),
        "findings": result.get("findings", []),
        "sources": result.get("sources", []),
        "narrative": result.get("narrative"),
    }


@mcp.tool(
    annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)
)
def get_review_status(run_id: str) -> dict:
    """Read approval/execution status without approving, rejecting or executing anything."""
    run = read_run(run_id)
    action = run.get("action")
    return {
        "run_id": run["id"],
        "status": run["status"],
        "action": {
            "id": action["id"],
            "status": action["status"],
            "result": action.get("result_json"),
        }
        if action
        else None,
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
