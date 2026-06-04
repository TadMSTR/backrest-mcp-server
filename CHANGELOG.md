# Changelog

## [0.2.0] — 2026-06-04

### Changed

- Rewritten from TypeScript/Node to Python/FastMCP to match forge MCP standard
- Renamed from `backrest-mcp-server` to `backrest-mcp`

### Added

- `get_config` — read Backrest config (repos, plans)
- `list_snapshots` — list snapshots for a repo or plan
- `list_snapshot_files` — browse files within a snapshot
- `get_summary` — 30-day dashboard stats (success/fail counts, bytes added)
- `do_repo_task` — trigger prune/check/stats/unlock/index on a repo
- `forget_snapshot` — forget a specific snapshot (requires ALLOW_DESTRUCTIVE + confirm token)
- `restore_snapshot` — restore a snapshot to a staging path (requires ALLOW_DESTRUCTIVE + path guard)
- `cancel_operation` — cancel a running operation
- `trigger_backup` gains `dry_run` parameter
- `safety.py` — layered safety controls: READONLY mode, ALLOW_DESTRUCTIVE gate, restore path
  guard, forget confirmation token, audit log
- `ecosystem.config.js` — PM2 config with safe defaults (READONLY=true)
- `observability.py` — structlog JSON logging + optional InfluxDB metrics
- `tests/` — pytest + respx mocks (test_client, test_tools, test_safety)

## [0.1.1] — 2026-03-12

### Security

- **Input validation hardened** — plan IDs and repo IDs now validated with zod regex schema
  (`/^[\w\-]+$/`, 1–128 chars) before use in API requests; rejects path traversal and
  injection characters.
- **`zod` pinned** — explicit version pin in `package.json` to prevent supply-chain drift.
- **`.env.example` added** — documents required env vars without shipping real credentials.
- **TLS documentation** — README updated with self-signed cert and mTLS guidance for
  non-default Backrest deployments.

## [0.1.0] — 2026-03-09

### Added

- Initial release of `backrest-mcp-server` — TypeScript MCP server (stdio) wrapping the
  Backrest backup manager REST API
- `trigger-backup(planId)` — POST to Backrest `/v1.Backrest/Backup`; blocks until completion
- `get-operations(planId?, repoId?, limit)` — Fetch recent operation history with optional
  plan/repo filter
- Basic Auth support via `BACKREST_USERNAME` / `BACKREST_PASSWORD` env vars (optional)
- Env vars: `BACKREST_URL` (default: `http://localhost:9898`), `BACKREST_USERNAME`, `BACKREST_PASSWORD`
