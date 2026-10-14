"""Verify the optional stdio MCP protocol against a persisted fixture review."""

import asyncio
import json
import os
import sys
from datetime import UTC, datetime

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from integration_env import ROOT, environment


async def main():
    env = environment()
    headers = {"X-Demo-Token": env["ASSISTANT_DEMO_REQUESTER_TOKEN"]}
    with httpx.Client(timeout=30) as client:
        response = client.post(
            env["ASSISTANT_BASE_URL"] + "/api/reviews",
            headers=headers,
            json={
                "listing_id": "ILAN-1001",
                "workflow": "listing_review",
                "request_text": "MCP fixture review: inspect without approving.",
            },
        )
        response.raise_for_status()
        run = response.json()
    parameters = StdioServerParameters(
        command=sys.executable,
        args=[str(ROOT / "examples/mcp/server.py")],
        env={**os.environ, "ASSISTANT_BASE_URL": env["ASSISTANT_BASE_URL"]},
    )
    async with stdio_client(parameters) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = {tool.name for tool in tools.tools}
            assert names == {"get_listing_analysis", "get_review_status"}
            for tool in tools.tools:
                assert tool.annotations.readOnlyHint is True
                assert tool.annotations.destructiveHint is False
            for name in names:
                result = await session.call_tool(name, {"run_id": run["id"]})
                assert result.isError is False
    with httpx.Client(timeout=10) as client:
        after = client.get(
            env["ASSISTANT_BASE_URL"] + "/api/runs/" + run["id"], headers=headers
        ).json()
        assert after["action"]["status"] == "pending_approval"
        assert after["action"]["result_json"] is None
    report = {
        "verified_at": datetime.now(UTC).isoformat(),
        "transport": "stdio",
        "tools": sorted(names),
        "checks": {
            "protocol_initialization": True,
            "both_read_tools_called": True,
            "no_action_executed": True,
        },
    }
    (ROOT / "docs/verification").mkdir(exist_ok=True)
    (ROOT / "docs/verification/mcp.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("MCP stdio: initialization and both read-only tools verified; no action executed.")


if __name__ == "__main__":
    asyncio.run(main())
