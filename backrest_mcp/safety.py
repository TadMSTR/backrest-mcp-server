"""
Layered safety controls for backrest-mcp.

All controls are opt-in to enable (default: most restrictive).
No env vars needed to stay safe — only set them to unlock writes.

Controls:
  BACKREST_READONLY (default: true)        — register only read-only tools
  BACKREST_ALLOW_DESTRUCTIVE (default: false) — also register forget/restore
  BACKREST_RESTORE_ALLOWED_PREFIX          — restore target path prefix
  BACKREST_AUDIT_LOG                       — path for write-op audit log (JSONL)
"""

from __future__ import annotations

import json
import os
import pathlib
import time

# Master read-only switch. When true, no mutating tools are registered.
READONLY = os.getenv("BACKREST_READONLY", "true").lower() in ("1", "true", "yes")

# Separate gate for irreversible tools (forget_snapshot, restore_snapshot).
# Requires BACKREST_READONLY=false AND BACKREST_ALLOW_DESTRUCTIVE=true.
ALLOW_DESTRUCTIVE = (
    not READONLY
    and os.getenv("BACKREST_ALLOW_DESTRUCTIVE", "false").lower() in ("1", "true", "yes")
)

# Restore operations must write under this prefix. Prevents restoring over live data.
RESTORE_ALLOWED_PREFIX = os.getenv(
    "BACKREST_RESTORE_ALLOWED_PREFIX", "/tmp/backrest-restore/"
)

# Audit log path. Every non-read tool call is appended here as a JSON line.
AUDIT_LOG = os.getenv("BACKREST_AUDIT_LOG", "")


def audit_log(tool: str, args: dict) -> None:
    """Append a JSONL audit entry for a write/destructive tool call.

    Credentials are never included — the caller must not pass auth env values
    in the args dict.
    """
    if not AUDIT_LOG:
        return
    entry = {"ts": time.time(), "tool": tool, "args": args}
    pathlib.Path(AUDIT_LOG).parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")
