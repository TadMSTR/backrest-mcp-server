# backrest-mcp

Python/FastMCP MCP server (stdio transport) wrapping the Backrest backup manager REST API.

## What it does

Provides MCP tools for querying backup operations, listing snapshots, reading config,
browsing snapshot contents, triggering backups, running repo maintenance tasks, and
(with explicit opt-in) forgetting snapshots and restoring data to staging paths.

## Tools

**Always registered (read-only):**
- `get_config()` — Read Backrest configuration (repos, plans, global settings)
- `list_snapshots(repo_id?, plan_id?)` — List snapshots, optionally filtered
- `list_snapshot_files(repo_guid, snapshot_id, path?)` — Browse files within a snapshot
- `get_summary()` — 30-day dashboard stats per repo and plan
- `get_operations(plan_id?, repo_id?, limit?)` — Recent operation history with status icons

**Registered when `BACKREST_READONLY=false`:**
- `trigger_backup(plan_id, dry_run?)` — Trigger a backup plan
- `do_repo_task(repo_id, task)` — Run maintenance: index/prune/check/stats/unlock/forget
- `cancel_operation(operation_id)` — Cancel a running operation

**Registered when `BACKREST_ALLOW_DESTRUCTIVE=true` (requires `READONLY=false`):**
- `forget_snapshot(snapshot_id, repo_id, confirm, plan_id?)` — Permanently forget a snapshot
- `restore_snapshot(snapshot_id, repo_id, path, target, plan_id?)` — Restore to staging path

## Structure

```
backrest_mcp/
  __init__.py
  client.py        BackrestClient — connect-rpc-over-HTTP POST + JSON, optional Basic Auth
  models.py        Pydantic models for API responses (camelCase field names from proto)
  safety.py        Safety controls — READONLY flag, ALLOW_DESTRUCTIVE gate, path guard, audit log
  server.py        FastMCP server — conditional tool registration, all 10 tools
  observability.py structlog JSON logging + optional InfluxDB/NATS metrics
tests/
  test_client.py   HTTP mechanics, auth, error handling
  test_tools.py    End-to-end tool tests via FastMCP test client
  test_safety.py   Safety control unit tests — gating, confirm tokens, path guards, audit log
pyproject.toml
ecosystem.config.js  PM2 config (BACKREST_READONLY=true default)
```

## Configuration

| Env var | Default | Purpose |
|---------|---------|---------|
| `BACKREST_URL` | `http://localhost:9898` | Backrest base URL |
| `BACKREST_USERNAME` | — | Basic Auth username (optional) |
| `BACKREST_PASSWORD` | — | Basic Auth password (optional) |
| `BACKREST_READONLY` | `true` | Disable all write tools when true |
| `BACKREST_ALLOW_DESTRUCTIVE` | `false` | Enable forget_snapshot + restore_snapshot |
| `BACKREST_RESTORE_ALLOWED_PREFIX` | `/tmp/backrest-restore/` | Restore target path guard |
| `BACKREST_AUDIT_LOG` | — | JSONL audit log path for write ops |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `LOG_FILE` | stderr | Log file path |
| `INFLUXDB_URL` | — | InfluxDB for metrics (optional) |

## Safety controls (`safety.py`)

Four layered controls gate write and destructive operations:

1. **READONLY flag** — `BACKREST_READONLY=true` (default) prevents write tools from being
   registered at startup. No write calls are possible.

2. **ALLOW_DESTRUCTIVE gate** — `BACKREST_ALLOW_DESTRUCTIVE=false` (default) prevents
   `forget_snapshot` and `restore_snapshot` from being registered even when READONLY=false.

3. **Forget confirmation token** — `forget_snapshot` requires `confirm=f"FORGET:{snapshot_id}"`.
   Forces the caller to name the exact snapshot being deleted.

4. **Restore path guard** — `restore_snapshot` validates `target` with `os.path.realpath()`
   against `BACKREST_RESTORE_ALLOWED_PREFIX`. Path traversal attempts are blocked.

5. **Audit log** — all write tool calls append a JSONL entry to `BACKREST_AUDIT_LOG` (if set).
   Credential values are never included.

## Key architecture decisions

- **Connect-rpc-over-HTTP** — all Backrest API calls are `POST {base_url}/v1.Backrest/{Method}`
  with JSON body. No gRPC transport needed.
- **No credentials in logs** — `BACKREST_USERNAME`/`BACKREST_PASSWORD` are used only in the
  httpx Basic Auth tuple and never written to any log or audit entry.
- **lru_cache on get_client()** — single BackrestClient instance reused for the server lifetime.
- **Opt-in write access** — safe default requires no configuration. Set env vars explicitly to unlock.

## Build

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Git workflow

Branch before editing — do not commit directly to `main`.
Feature branches: `feature/<slug>` or `fix/<slug>`.
