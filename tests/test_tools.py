"""
End-to-end tool tests using FastMCP 3.x direct call API.

Tests the read-only tools (always registered). Write/destructive tools are
covered in test_safety.py since they depend on env var gating.
"""

from __future__ import annotations

import sys

import httpx
import pytest
import respx

BASE_URL = "http://localhost:9898"


@pytest.fixture(autouse=True)
def reset_client_cache():
    from backrest_mcp.client import get_client
    get_client.cache_clear()
    yield
    get_client.cache_clear()


@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("BACKREST_URL", BASE_URL)
    monkeypatch.setenv("BACKREST_USERNAME", "")
    monkeypatch.setenv("BACKREST_PASSWORD", "")
    monkeypatch.setenv("BACKREST_READONLY", "true")
    monkeypatch.setenv("BACKREST_ALLOW_DESTRUCTIVE", "false")


@pytest.fixture
def mcp_server(mock_env):
    """Return a fresh FastMCP server instance with env vars applied."""
    for mod in ["backrest_mcp.server", "backrest_mcp.safety"]:
        if mod in sys.modules:
            del sys.modules[mod]
    import backrest_mcp.server as srv
    return srv.mcp


async def test_get_summary_returns_dashboard(mcp_server):
    """get_summary returns dashboard data from the API."""
    summary_response = {
        "repoSummaries": [
            {
                "id": "local",
                "backupsSuccessLast30days": 28,
                "backupsFailedLast30days": 2,
                "bytesAddedLast30days": 1048576,
                "totalSnapshots": 120,
            }
        ],
        "planSummaries": [],
    }
    with respx.mock() as mock:
        mock.post(f"{BASE_URL}/v1.Backrest/GetSummaryDashboard").mock(
            return_value=httpx.Response(200, json=summary_response)
        )
        result = await mcp_server.call_tool("get_summary", {})

    assert result is not None
    assert not result.is_error
    text = result.content[0].text
    assert "local" in text or "repoSummaries" in text


async def test_get_operations_formats_output(mcp_server):
    """get_operations returns formatted lines with status icons."""
    ops_response = {
        "operations": [
            {
                "id": "op-1",
                "planId": "daily",
                "repoId": "local",
                "status": "STATUS_SUCCESS",
                "unixTimeStartMs": 1748000000000,
                "unixTimeEndMs": 1748000060000,
                "displayMessage": "Backup complete",
            }
        ]
    }
    with respx.mock() as mock:
        mock.post(f"{BASE_URL}/v1.Backrest/GetOperations").mock(
            return_value=httpx.Response(200, json=ops_response)
        )
        result = await mcp_server.call_tool("get_operations", {"limit": 5})

    assert result is not None
    text = result.content[0].text
    assert "✓" in text or "daily" in text


async def test_trigger_backup_absent_in_readonly(mcp_server):
    """trigger_backup is not registered when BACKREST_READONLY=true."""
    tools = await mcp_server.list_tools()
    names = [t.name for t in tools]
    assert "trigger_backup" not in names


async def test_readonly_tools_always_present(mcp_server):
    """Read-only tools are always registered regardless of safety flags."""
    tools = await mcp_server.list_tools()
    names = [t.name for t in tools]
    for expected in ["get_config", "list_snapshots", "list_snapshot_files", "get_summary", "get_operations"]:
        assert expected in names, f"{expected} missing from tool list"
