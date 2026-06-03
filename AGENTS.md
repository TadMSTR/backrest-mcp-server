# backrest-mcp-server

TypeScript/Node MCP server (stdio transport) wrapping the Backrest backup manager REST API.

## What it does

Provides MCP tools for triggering backup plans and querying operation history from a Backrest instance.

## Tools

- `trigger-backup(planId)` — POST to `/v1.Backrest/Backup`. Blocks until the backup completes. Plan ID validated with `planIdSchema`.
- `get-operations(planId?, repoId?, limit)` — Fetch recent operation history, optionally filtered by plan or repo.

Check `src/index.ts` for the full `server.tool()` list — additional tools may exist.

## Structure

```
src/
  index.ts    Single-file server — McpServer, all tools, Backrest API client
package.json  deps: @modelcontextprotocol/sdk, zod
tsconfig.json TypeScript config
```

## Configuration

| Env var               | Default                    | Purpose                          |
|-----------------------|----------------------------|----------------------------------|
| `BACKREST_URL`        | `http://localhost:9898`    | Backrest base URL                |
| `BACKREST_USERNAME`   | —                          | Basic Auth username (optional)   |
| `BACKREST_PASSWORD`   | —                          | Basic Auth password (optional)   |

## Key architecture decisions

- **Input validation with zod before any API call** — plan IDs use `planIdSchema` (`/^[\w\-]+$/`, 1–128 chars), repo IDs use `repoIdSchema` with the same pattern. These IDs are passed directly into URL paths — do not weaken the regex.
- **No auth tokens in logs** — credentials are used only in the Authorization header and are never written to stdout, stderr, or any log output.

## Build

```bash
npm install && npm run build
```

Check `package.json` for test scripts.

## Git workflow

Branch before editing — do not commit directly to `main`.
