# Changelog

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
