import importlib.util
from pathlib import Path

import pytest

SERVER = Path(__file__).resolve().parents[2] / "examples/mcp/server.py"


@pytest.fixture
def module():
    pytest.importorskip("mcp", reason="Install optional mcp group to check this integration")
    spec = importlib.util.spec_from_file_location("portfolio_mcp", SERVER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_mcp_rejects_nonlocal_origins(module, monkeypatch):
    monkeypatch.setenv("ASSISTANT_BASE_URL", "https://example.invalid")
    with pytest.raises(ValueError, match="local backend"):
        module.base_url()


def test_mcp_rejects_path_payload_before_http(module):
    with pytest.raises(ValueError):
        module.read_run("../../private")


def test_read_status_has_no_write_side_effect(module, monkeypatch):
    monkeypatch.setattr(
        module,
        "read_run",
        lambda identifier: {
            "id": identifier,
            "status": "awaiting_approval",
            "action": {"id": "test", "status": "pending_approval", "result_json": None},
        },
    )
    result = module.get_review_status("fixture-id")
    assert result["action"]["status"] == "pending_approval"
    assert result["action"]["result"] is None
