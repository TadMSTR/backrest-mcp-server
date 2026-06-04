# backrest-mcp

MCP server for [Backrest](https://github.com/garethgeorge/backrest) — a web UI and orchestrator for restic backups.

Python/FastMCP rewrite of `backrest-mcp-server`. Covers the full useful surface of the Backrest REST API with layered safety controls to protect backup data.

## Tools

| Tool | Description | Requires |
|------|-------------|---------|
| `get_config` | Read Backrest configuration (repos, plans) | — |
| `list_snapshots` | List snapshots, optionally filtered by repo or plan | — |
| `list_snapshot_files` | Browse files within a snapshot | — |
| `get_summary` | 30-day dashboard stats per repo and plan | — |
| `get_operations` | Recent operation history with status icons | — |
| `trigger_backup` | Trigger a backup plan (dry_run supported) | `BACKREST_READONLY=false` |
| `do_repo_task` | Run maintenance: prune/check/stats/unlock/index | `BACKREST_READONLY=false` |
| `cancel_operation` | Cancel a running operation | `BACKREST_READONLY=false` |
| `forget_snapshot` | Permanently forget a snapshot (confirm token required) | `BACKREST_ALLOW_DESTRUCTIVE=true` |
| `restore_snapshot` | Restore snapshot to a staging path | `BACKREST_ALLOW_DESTRUCTIVE=true` |

Default state: **read-only** — only the top 5 tools are registered. No write calls are possible without explicit opt-in.

## Safety Controls

Backups are critical data. Four controls gate write and destructive operations:

**1. Read-only mode** (default: on)
```
BACKREST_READONLY=true   # no write tools registered (default)
BACKREST_READONLY=false  # enables trigger_backup, do_repo_task, cancel_operation
```

**2. Destructive gate** (default: off)
```
BACKREST_ALLOW_DESTRUCTIVE=false  # forget/restore never registered (default)
BACKREST_ALLOW_DESTRUCTIVE=true   # enables forget_snapshot, restore_snapshot
                                   # requires BACKREST_READONLY=false
```

**3. Forget confirmation token**

`forget_snapshot` requires `confirm=f"FORGET:{snapshot_id}"`. The caller must name the exact snapshot being deleted.

**4. Restore path guard**

`restore_snapshot` validates the `target` path against `BACKREST_RESTORE_ALLOWED_PREFIX` (default: `/tmp/backrest-restore/`) using `os.path.realpath()`. Path traversal attempts are blocked. After verifying restored files, move them manually.

**5. Audit log**

Set `BACKREST_AUDIT_LOG=/path/to/audit.jsonl` to log all write operations. Credential values are never included.

## Configuration

| Env var | Default | Purpose |
|---------|---------|---------|
| `BACKREST_URL` | `http://localhost:9898` | Backrest base URL |
| `BACKREST_USERNAME` | — | Basic Auth username (optional) |
| `BACKREST_PASSWORD` | — | Basic Auth password |
| `BACKREST_READONLY` | `true` | Disable all write tools |
| `BACKREST_ALLOW_DESTRUCTIVE` | `false` | Enable forget/restore (requires READONLY=false) |
| `BACKREST_RESTORE_ALLOWED_PREFIX` | `/tmp/backrest-restore/` | Restore target path guard |
| `BACKREST_AUDIT_LOG` | — | JSONL audit log for write ops |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `LOG_FILE` | stderr | Log file path |
| `INFLUXDB_URL` | — | Optional InfluxDB metrics |

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

For development/testing:
```bash
pip install -e ".[dev]"
pytest
```

## Claude Desktop Config

```json
{
  "mcpServers": {
    "backrest": {
      "command": "/path/to/backrest-mcp/.venv/bin/python",
      "args": ["-m", "backrest_mcp.server"],
      "env": {
        "BACKREST_URL": "http://localhost:9898",
        "BACKREST_USERNAME": "your-username",
        "BACKREST_PASSWORD": "your-password",
        "BACKREST_READONLY": "true"
      }
    }
  }
}
```

Omit `BACKREST_USERNAME` and `BACKREST_PASSWORD` if Backrest auth is disabled.

## TLS

If connecting to an HTTPS endpoint with a private or self-signed CA:

```
REQUESTS_CA_BUNDLE=/path/to/ca.crt
```

httpx respects this env var. Do **not** disable TLS verification.

## Auth Architecture

Credentials flow: env vars → `BackrestClient.__init__` → httpx Basic Auth tuple → Authorization header.
Credentials are never written to logs, audit entries, or MCP tool responses.

## Backrest Deployment

Backrest is not yet deployed on forge. The `ecosystem.config.js` targets `http://localhost:9898` — the planned address once the `backrest-forge-deploy-2026-06` sysadmin task completes.
