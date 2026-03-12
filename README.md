# backrest-mcp-server

MCP server for [Backrest](https://github.com/garethgeorge/backrest) — a web UI and orchestrator for restic backups.

## Tools

- **trigger-backup** — Trigger a backup plan by plan ID
- **get-operations** — Fetch operation history, optionally filtered by plan or repo

## Configuration

Set via environment variables in your Claude Desktop MCP config:

| Variable | Default | Description |
|---|---|---|
| `BACKREST_URL` | `http://localhost:9898` | Backrest base URL |
| `BACKREST_USERNAME` | _(empty)_ | Username for basic auth (if auth is enabled) |
| `BACKREST_PASSWORD` | _(empty)_ | Password for basic auth |

A `.env.example` template is included in the repo root.

### TLS

If connecting to an HTTPS endpoint with a private or self-signed CA, set:

```
NODE_EXTRA_CA_CERTS=/path/to/ca.crt
```

Do **not** use `NODE_TLS_REJECT_UNAUTHORIZED=0` — that disables all certificate verification globally.

## Claude Desktop Config

```json
{
  "mcpServers": {
    "backrest": {
      "command": "node",
      "args": ["/path/to/backrest-mcp-server/build/src/index.js"],
      "env": {
        "BACKREST_URL": "http://localhost:9898",
        "BACKREST_USERNAME": "your-username",
        "BACKREST_PASSWORD": "your-password"
      }
    }
  }
}
```

For Docker users, set `BACKREST_URL` to the container's address (e.g. `http://192.168.1.x:9898`).

If Backrest auth is disabled, omit `BACKREST_USERNAME` and `BACKREST_PASSWORD`.

## Build

```bash
pnpm install
pnpm run build
```
