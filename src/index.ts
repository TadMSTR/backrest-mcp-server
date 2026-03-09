#!/usr/bin/env node
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const BACKREST_URL = (process.env.BACKREST_URL ?? "http://localhost:9898").replace(/\/$/, "");
const BACKREST_USERNAME = process.env.BACKREST_USERNAME ?? "";
const BACKREST_PASSWORD = process.env.BACKREST_PASSWORD ?? "";

function authHeaders(): Record<string, string> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (BACKREST_USERNAME && BACKREST_PASSWORD) {
    const encoded = Buffer.from(`${BACKREST_USERNAME}:${BACKREST_PASSWORD}`).toString("base64");
    headers["Authorization"] = `Basic ${encoded}`;
  }
  return headers;
}

async function backrestPost(endpoint: string, body: unknown): Promise<unknown> {
  const url = `${BACKREST_URL}/${endpoint}`;
  const res = await fetch(url, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`Backrest API error ${res.status}: ${text}`);
  }

  return res.json();
}

const server = new McpServer({
  name: "backrest-mcp-server",
  version: "0.1.0",
});


server.tool(
  "trigger-backup",
  "Trigger a Backrest backup plan by plan ID. Blocks until the backup completes (or times out, in which case the backup continues in the background).",
  {
    planId: z.string().describe("The Backrest plan ID to trigger"),
  },
  async ({ planId }) => {
    try {
      await backrestPost("v1.Backrest/Backup", { value: planId });
      return {
        content: [{ type: "text", text: `Backup plan "${planId}" completed successfully.` }],
      };
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      return {
        content: [{ type: "text", text: `Backup trigger failed: ${msg}` }],
        isError: true,
      };
    }
  }
);

server.tool(
  "get-operations",
  "Fetch recent operation history from Backrest. Optionally filter by plan ID or repo ID. Returns status, timestamps, and any errors.",
  {
    planId: z.string().optional().describe("Filter operations by plan ID"),
    repoId: z.string().optional().describe("Filter operations by repository ID"),
    limit: z.number().min(1).max(100).default(20).describe("Max number of operations to return"),
  },
  async ({ planId, repoId, limit }) => {
    type Operation = {
      id?: string | number;
      planId?: string;
      repoId?: string;
      status?: string;
      unixTimeStartMs?: string | number;
      unixTimeEndMs?: string | number;
      displayMessage?: string;
    };

    try {
      const selector: Record<string, string> = {};
      if (planId) selector.planId = planId;
      if (repoId) selector.repoId = repoId;

      const body = Object.keys(selector).length > 0 ? { selector } : { selector: {} };
      const data = (await backrestPost("v1.Backrest/GetOperations", body)) as { operations?: Operation[] };

      const ops = (data.operations ?? []).slice(0, limit);

      if (ops.length === 0) {
        return { content: [{ type: "text", text: "No operations found." }] };
      }

      const lines: string[] = [`Operations (${ops.length} shown):`];

      for (const op of ops) {
        const startMs = op.unixTimeStartMs ? Number(op.unixTimeStartMs) : null;
        const endMs = op.unixTimeEndMs ? Number(op.unixTimeEndMs) : null;
        const startStr = startMs ? new Date(startMs).toLocaleString() : "?";
        const durationSec = startMs && endMs ? ((endMs - startMs) / 1000).toFixed(0) : null;
        const durationStr = durationSec ? ` (${durationSec}s)` : "";
        const status = op.status ?? "unknown";
        const statusIcon = status === "STATUS_SUCCESS" ? "✓" : status === "STATUS_ERROR" ? "✗" : status === "STATUS_INPROGRESS" ? "⟳" : "•";
        const plan = op.planId ? ` plan=${op.planId}` : "";
        const repo = op.repoId ? ` repo=${op.repoId}` : "";
        lines.push(`  ${statusIcon} ${startStr}${durationStr}${plan}${repo}`);
        if (op.displayMessage) lines.push(`    ${op.displayMessage}`);
      }

      return { content: [{ type: "text", text: lines.join("\n") }] };
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      return {
        content: [{ type: "text", text: `Failed to fetch operations: ${msg}` }],
        isError: true,
      };
    }
  }
);

const transport = new StdioServerTransport();
await server.connect(transport);
