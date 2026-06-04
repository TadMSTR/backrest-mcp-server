"""
backrest-mcp — FastMCP server wrapping the Backrest backup manager REST API.

Tool registration is gated by safety flags from backrest_mcp.safety:
  Always registered (read-only):
    get_config, list_snapshots, list_snapshot_files, get_summary, get_operations

  Registered when BACKREST_READONLY=false:
    trigger_backup, do_repo_task, cancel_operation

  Registered when BACKREST_READONLY=false AND BACKREST_ALLOW_DESTRUCTIVE=true:
    forget_snapshot, restore_snapshot
"""

from __future__ import annotations

import datetime
import os
import pathlib
import time
from typing import Literal, Optional

import structlog
from fastmcp import FastMCP

from .client import BackrestClient, get_client
from .models import (
    ListSnapshotFilesResponse,
    OperationList,
    SnapshotList,
    SummaryDashboard,
)
from .observability import emit_metric
from .safety import ALLOW_DESTRUCTIVE, READONLY, RESTORE_ALLOWED_PREFIX, audit_log, validate_backrest_id

log = structlog.get_logger(__name__)

mcp = FastMCP(
    name="backrest-mcp",
    instructions=(
        "Backrest MCP server. Provides read access to backup operations, snapshots, "
        "configuration, and dashboard stats. Write tools (trigger_backup, do_repo_task, "
        "cancel_operation) are only available when BACKREST_READONLY=false. "
        "Destructive tools (forget_snapshot, restore_snapshot) require BACKREST_ALLOW_DESTRUCTIVE=true. "
        "Backrest is not yet deployed on forge — connect to it once the sysadmin completes "
        "the backrest-forge-deploy-2026-06 plan."
    ),
)

_REPO_TASK_MAP: dict[str, int] = {
    "index": 1,
    "prune": 2,
    "check": 3,
    "stats": 4,
    "unlock": 5,
    "forget": 6,
}

_STATUS_ICONS: dict[str, str] = {
    "STATUS_SUCCESS": "✓",
    "STATUS_ERROR": "✗",
    "STATUS_INPROGRESS": "⟳",
    "STATUS_PENDING": "○",
    "STATUS_WARNING": "⚠",
    "STATUS_CANCELLED": "⊘",
}


def _tool_error(tool: str, err: Exception) -> dict:
    log.error("tool_error", tool=tool, error=str(err))
    return {"error": "tool call failed — check server logs for details"}


def _fmt_ms(ms: Optional[int]) -> str:
    if ms is None:
        return "—"
    return datetime.datetime.fromtimestamp(ms / 1000, tz=datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _fmt_duration(start_ms: Optional[int], end_ms: Optional[int]) -> str:
    if start_ms is None or end_ms is None:
        return ""
    secs = (end_ms - start_ms) / 1000
    if secs < 60:
        return f"{secs:.0f}s"
    return f"{secs / 60:.1f}m"


# ---------------------------------------------------------------------------
# Read-only tools — always registered
# ---------------------------------------------------------------------------

@mcp.tool()
async def get_config() -> dict:
    """Read the Backrest configuration (repos, plans, global settings).

    Returns the full Backrest config as a dict. Does not expose credentials.
    """
    client = get_client()
    t0 = time.perf_counter()
    try:
        result = await client.post("GetConfig", {})
        await emit_metric("backrest_tool", {"tool": "get_config"}, {"duration_ms": (time.perf_counter() - t0) * 1000})
        return result
    except Exception as e:
        return _tool_error("get_config", e)


@mcp.tool()
async def list_snapshots(
    repo_id: Optional[str] = None,
    plan_id: Optional[str] = None,
) -> dict:
    """List snapshots in a Backrest repo, optionally filtered by repo or plan.

    Args:
        repo_id: Backrest repository ID to list snapshots for.
        plan_id: Plan ID to filter snapshots. Can be combined with repo_id.

    Returns a list of snapshots with ID, timestamp, hostname, paths, and tags.
    """
    client = get_client()
    try:
        if repo_id:
            validate_backrest_id("repo_id", repo_id)
        if plan_id:
            validate_backrest_id("plan_id", plan_id)
    except ValueError as e:
        return _tool_error("list_snapshots", e)
    body: dict = {}
    if repo_id:
        body["repoId"] = repo_id
    if plan_id:
        body["planId"] = plan_id
    t0 = time.perf_counter()
    try:
        raw = await client.post("ListSnapshots", body)
        parsed = SnapshotList.model_validate(raw)
        await emit_metric("backrest_tool", {"tool": "list_snapshots"}, {"duration_ms": (time.perf_counter() - t0) * 1000, "count": len(parsed.snapshots)})
        return {"snapshots": [s.model_dump(exclude_none=True) for s in parsed.snapshots]}
    except Exception as e:
        return _tool_error("list_snapshots", e)


@mcp.tool()
async def list_snapshot_files(
    repo_guid: str,
    snapshot_id: str,
    path: str = "/",
) -> dict:
    """Browse files within a specific snapshot.

    Args:
        repo_guid: The repository GUID (not the repo ID — use list_snapshots to find it).
        snapshot_id: Snapshot ID to browse.
        path: Directory path within the snapshot to list. Defaults to root "/".

    Returns a list of file/directory entries at the given path.
    """
    client = get_client()
    try:
        validate_backrest_id("repo_guid", repo_guid)
        validate_backrest_id("snapshot_id", snapshot_id)
    except ValueError as e:
        return _tool_error("list_snapshot_files", e)
    # SECURITY[deferred]: path not validated — goes in JSON body to local HTTP API; Backrest validates server-side.
    # Ticket: BKRST-2. Audit: 2026-06-04/backrest-mcp-2026-06.
    body = {"repoGuid": repo_guid, "snapshotId": snapshot_id, "path": path}
    t0 = time.perf_counter()
    try:
        raw = await client.post("ListSnapshotFiles", body)
        parsed = ListSnapshotFilesResponse.model_validate(raw)
        await emit_metric("backrest_tool", {"tool": "list_snapshot_files"}, {"duration_ms": (time.perf_counter() - t0) * 1000})
        return {"path": parsed.path, "entries": [e.model_dump(exclude_none=True) for e in parsed.entries]}
    except Exception as e:
        return _tool_error("list_snapshot_files", e)


@mcp.tool()
async def get_summary() -> dict:
    """Get the Backrest dashboard summary — 30-day stats per repo and plan.

    Returns backup success/fail counts, bytes added, total snapshots, and
    next scheduled backup time for each repo and plan.
    """
    client = get_client()
    t0 = time.perf_counter()
    try:
        raw = await client.post("GetSummaryDashboard", {})
        parsed = SummaryDashboard.model_validate(raw)
        await emit_metric("backrest_tool", {"tool": "get_summary"}, {"duration_ms": (time.perf_counter() - t0) * 1000})
        return parsed.model_dump(exclude_none=True)
    except Exception as e:
        return _tool_error("get_summary", e)


@mcp.tool()
async def get_operations(
    plan_id: Optional[str] = None,
    repo_id: Optional[str] = None,
    limit: int = 20,
) -> dict:
    """List recent backup operations, optionally filtered by plan or repo.

    Args:
        plan_id: Filter operations by plan ID.
        repo_id: Filter operations by repo ID.
        limit: Maximum number of operations to return (default 20).

    Returns a formatted list of operations with status icons and durations.
    """
    client = get_client()
    try:
        if plan_id:
            validate_backrest_id("plan_id", plan_id)
        if repo_id:
            validate_backrest_id("repo_id", repo_id)
    except ValueError as e:
        return _tool_error("get_operations", e)
    selector: dict = {}
    if plan_id:
        selector["planId"] = plan_id
    if repo_id:
        selector["repoId"] = repo_id
    body: dict = {"lastN": limit}
    if selector:
        body["selector"] = selector

    t0 = time.perf_counter()
    try:
        raw = await client.post("GetOperations", body)
        parsed = OperationList.model_validate(raw)
        await emit_metric("backrest_tool", {"tool": "get_operations"}, {"duration_ms": (time.perf_counter() - t0) * 1000, "count": len(parsed.operations)})

        lines = []
        for op in parsed.operations:
            icon = _STATUS_ICONS.get(op.status or "", "?")
            ts = _fmt_ms(op.unixTimeStartMs)
            dur = _fmt_duration(op.unixTimeStartMs, op.unixTimeEndMs)
            plan = op.planId or "—"
            repo = op.repoId or "—"
            msg = op.displayMessage or ""
            line = f"{icon} [{ts}] plan={plan} repo={repo}"
            if dur:
                line += f" ({dur})"
            if msg:
                line += f" — {msg}"
            lines.append(line)

        return {"operations": lines, "count": len(lines)}
    except Exception as e:
        return _tool_error("get_operations", e)


# ---------------------------------------------------------------------------
# Write tools — registered only when BACKREST_READONLY=false
# ---------------------------------------------------------------------------

if not READONLY:
    @mcp.tool()
    async def trigger_backup(
        plan_id: str,
        dry_run: bool = False,
    ) -> dict:
        """Trigger a backup for a specific plan.

        Args:
            plan_id: The Backrest plan ID to back up.
            dry_run: If true, simulate the backup without writing data (default false).

        Returns the operation ID of the triggered backup.
        """
        try:
            validate_backrest_id("plan_id", plan_id)
        except ValueError as e:
            return _tool_error("trigger_backup", e)
        audit_log("trigger_backup", {"plan_id": plan_id, "dry_run": dry_run})
        client = get_client()
        body = {"value": plan_id, "dryRun": dry_run}
        t0 = time.perf_counter()
        try:
            result = await client.post("Backup", body)
            await emit_metric("backrest_tool", {"tool": "trigger_backup"}, {"duration_ms": (time.perf_counter() - t0) * 1000})
            return result
        except Exception as e:
            return _tool_error("trigger_backup", e)

    @mcp.tool()
    async def do_repo_task(
        repo_id: str,
        task: Literal["index", "prune", "check", "stats", "unlock", "forget"],
    ) -> dict:
        """Run a maintenance task on a Backrest repository.

        Args:
            repo_id: The Backrest repository ID.
            task: Task to run — one of: index, prune, check, stats, unlock, forget.
                  prune: Remove snapshots outside retention policy.
                  check: Verify repository integrity.
                  stats: Recalculate repository statistics.
                  unlock: Remove stale locks.
                  index: Re-index snapshot metadata.
                  forget: Apply forget/retention policy without pruning data.

        Returns the task result from Backrest.
        """
        try:
            validate_backrest_id("repo_id", repo_id)
        except ValueError as e:
            return _tool_error("do_repo_task", e)
        audit_log("do_repo_task", {"repo_id": repo_id, "task": task})
        client = get_client()
        task_int = _REPO_TASK_MAP[task]
        body = {"repoId": repo_id, "task": task_int}
        t0 = time.perf_counter()
        try:
            result = await client.post("DoRepoTask", body)
            await emit_metric("backrest_tool", {"tool": "do_repo_task"}, {"duration_ms": (time.perf_counter() - t0) * 1000})
            return result
        except Exception as e:
            return _tool_error("do_repo_task", e)

    @mcp.tool()
    async def cancel_operation(operation_id: str) -> dict:
        """Cancel a running Backrest operation.

        Args:
            operation_id: The operation ID to cancel (from get_operations).

        Returns the cancel result.
        """
        try:
            validate_backrest_id("operation_id", operation_id)
        except ValueError as e:
            return _tool_error("cancel_operation", e)
        audit_log("cancel_operation", {"operation_id": operation_id})
        client = get_client()
        t0 = time.perf_counter()
        try:
            result = await client.post("Cancel", {"value": operation_id})
            await emit_metric("backrest_tool", {"tool": "cancel_operation"}, {"duration_ms": (time.perf_counter() - t0) * 1000})
            return result
        except Exception as e:
            return _tool_error("cancel_operation", e)


# ---------------------------------------------------------------------------
# Destructive tools — registered only when ALLOW_DESTRUCTIVE=true
# ---------------------------------------------------------------------------

if ALLOW_DESTRUCTIVE:
    @mcp.tool()
    async def forget_snapshot(
        snapshot_id: str,
        repo_id: str,
        confirm: str,
        plan_id: Optional[str] = None,
    ) -> dict:
        """Forget (permanently delete) a specific snapshot from a Backrest repo.

        This is IRREVERSIBLE. The snapshot data will be removed on the next prune.

        Args:
            snapshot_id: The snapshot ID to forget.
            repo_id: The repository containing the snapshot.
            confirm: Must equal "FORGET:<snapshot_id>" to proceed.
                     Example: for snapshot_id "abc123", pass confirm="FORGET:abc123"
            plan_id: Optional plan ID for the forget operation.

        Returns the forget result, or an error if confirmation is wrong.
        """
        try:
            validate_backrest_id("snapshot_id", snapshot_id)
            validate_backrest_id("repo_id", repo_id)
        except ValueError as e:
            return _tool_error("forget_snapshot", e)
        expected = f"FORGET:{snapshot_id}"
        if confirm != expected:
            return {
                "content": [{"type": "text", "text": f'Confirmation required. Pass confirm="{expected}" to proceed.'}],
                "isError": True,
            }

        audit_log("forget_snapshot", {"snapshot_id": snapshot_id, "repo_id": repo_id, "plan_id": plan_id})
        client = get_client()
        body: dict = {"repoId": repo_id, "snapshotId": snapshot_id}
        if plan_id:
            body["planId"] = plan_id
        t0 = time.perf_counter()
        try:
            result = await client.post("Forget", body)
            await emit_metric("backrest_tool", {"tool": "forget_snapshot"}, {"duration_ms": (time.perf_counter() - t0) * 1000})
            return result
        except Exception as e:
            return _tool_error("forget_snapshot", e)

    @mcp.tool()
    async def restore_snapshot(
        snapshot_id: str,
        repo_id: str,
        path: str,
        target: str,
        plan_id: Optional[str] = None,
    ) -> dict:
        """Restore a snapshot (or a path within it) to a target directory.

        The target must be under BACKREST_RESTORE_ALLOWED_PREFIX (default: /tmp/backrest-restore/).
        This prevents accidental restores over live data. After verifying the restored files,
        move them to the desired location manually.

        WARNING: The target directory will be overwritten.

        Args:
            snapshot_id: Snapshot ID to restore from.
            repo_id: Repository containing the snapshot.
            path: Path within the snapshot to restore (e.g. "/home/ted/docs" or "/").
            target: Local filesystem path to restore to. Must be under the allowed prefix.
            plan_id: Optional plan ID.

        Returns the restore operation result, or an error if target is outside allowed prefix.
        """
        try:
            validate_backrest_id("snapshot_id", snapshot_id)
            validate_backrest_id("repo_id", repo_id)
        except ValueError as e:
            return _tool_error("restore_snapshot", e)
        allowed = pathlib.Path(os.path.realpath(RESTORE_ALLOWED_PREFIX))
        resolved = pathlib.Path(os.path.realpath(target))
        if not resolved.is_relative_to(allowed):
            return {
                "content": [{"type": "text", "text": (
                    f"Restore target must be under {RESTORE_ALLOWED_PREFIX}. "
                    f"Restore to a staging path, verify, then move manually."
                )}],
                "isError": True,
            }

        audit_log("restore_snapshot", {"snapshot_id": snapshot_id, "repo_id": repo_id, "path": path, "target": target, "plan_id": plan_id})
        client = get_client()
        # SECURITY[deferred]: path (within-snapshot source) not validated — goes in JSON body to local HTTP API; Backrest validates server-side.
        # Ticket: BKRST-2. Audit: 2026-06-04/backrest-mcp-2026-06.
        body: dict = {
            "snapshotId": snapshot_id,
            "repoId": repo_id,
            "path": path,
            "target": target,
        }
        if plan_id:
            body["planId"] = plan_id
        t0 = time.perf_counter()
        try:
            result = await client.post("Restore", body)
            await emit_metric("backrest_tool", {"tool": "restore_snapshot"}, {"duration_ms": (time.perf_counter() - t0) * 1000})
            return result
        except Exception as e:
            return _tool_error("restore_snapshot", e)


def main() -> None:
    from backrest_mcp.observability import configure_logging
    configure_logging()
    mcp.run(transport="stdio")
