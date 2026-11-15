# VentureVision MCP server

VentureVision's pipeline as three tools any MCP client (Claude Code, Cursor, your own agent) can call:

| Tool | Input | Returns | Cost |
|---|---|---|---|
| `analyze_pitch` | `pitch_text` (40–5000 chars), `mode` (`market_scan` \| `pitch_lab`, default `market_scan`) | Memo summary: score, subscores, a verdict per claim with its evidence quote and URL, verdict counts, groundedness, competitors, risks, run cost | Live web research. One recorded run: 65 s, $0.1227, capped per run by `RUN_BUDGET_USD` (default $0.25) |
| `verify_claim` | `claim` (3–1000 chars), `evidence_text` (1–20000 chars) | `supported` / `unsupported` / `contradicted`, reasoning, the verbatim quote it rests on | One `gpt-4o-mini` call, no search |
| `get_eval_scores` | none | Latest stored accuracy per label for the heuristic baseline and the LLM verifier, dataset version and size | Free (reads `evals/results/`) |

Every tool declares an `outputSchema` and returns `structuredContent`. Input schemas are strict (`additionalProperties: false`, length and enum limits) and are validated before a tool runs.

## Connect in two minutes

**1. Install** (from the repo root; Python 3.12+):

```bash
python -m venv backend/.venv
backend/.venv/bin/pip install -r mcp/requirements.txt        # Windows: backend\.venv\Scripts\pip
```

**2. Keys.** `analyze_pitch` needs `OPENAI_API_KEY` and `TAVILY_API_KEY`; `verify_claim` needs `OPENAI_API_KEY`. The server reads them from its environment, or from `.env` at the repo root. `get_eval_scores` needs neither.

**3. Add the server to your client.** Replace `/abs/path/VentureVision` with your checkout. On Windows the interpreter is `backend\\.venv\\Scripts\\python.exe`.

Cursor: `.cursor/mcp.json` in your project, or `~/.cursor/mcp.json` for all projects:

```json
{
  "mcpServers": {
    "venture-vision": {
      "command": "/abs/path/VentureVision/backend/.venv/bin/python",
      "args": ["/abs/path/VentureVision/mcp/ventureVisionServer.py"],
      "env": {
        "OPENAI_API_KEY": "sk-...",
        "TAVILY_API_KEY": "tvly-..."
      }
    }
  }
}
```

Claude Code:

```bash
claude mcp add venture-vision \
  -e OPENAI_API_KEY=sk-... -e TAVILY_API_KEY=tvly-... \
  -- /abs/path/VentureVision/backend/.venv/bin/python /abs/path/VentureVision/mcp/ventureVisionServer.py
```

(Or put the same `mcpServers` block as above in a `.mcp.json` at your project root.)

**4. Try it.** Ask your agent: *"Use venture-vision to check this claim: 'The DevOps market is worth over $10B' against: 'DevOps Market Size Worth $12.85 Billion by 2025'"*, or *"get VentureVision's eval scores"*.

## Streamable HTTP

```bash
backend/.venv/bin/python mcp/ventureVisionServer.py --transport http --port 8765
# VentureVision MCP on http://127.0.0.1:8765/mcp
```

Cursor:

```json
{ "mcpServers": { "venture-vision": { "url": "http://127.0.0.1:8765/mcp" } } }
```

Claude Code:

```bash
claude mcp add --transport http venture-vision http://127.0.0.1:8765/mcp
```

The server binds to `127.0.0.1` by default. `analyze_pitch` spends your API credits, so the server refuses a non-loopback `--host` unless `VV_MCP_HTTP_TOKEN` is set. With a token, every request needs `Authorization: Bearer <token>` (Cursor: add `"headers": {"Authorization": "Bearer <token>"}`; Claude Code: `--header "Authorization: Bearer <token>"`).

## Errors

A failed call returns `isError: true` with one text block containing JSON:

```json
{"error": {"code": "missing_credentials", "message": "The server has no TAVILY_API_KEY configured.", "retryable": false, "hint": "Set the key in the MCP server's env block or in the repo's .env, then restart the server."}}
```

| `code` | `retryable` | Meaning |
|---|---|---|
| `invalid_input` | false | Arguments break the inputSchema (too short, unknown mode, unknown argument, blank text) |
| `missing_credentials` | false | The server lacks an API key the tool needs |
| `busy` | true | Two analyses are already running on this server |
| `upstream_unavailable` | true | OpenAI or every Tavily search failed |
| `bad_model_output` | true | The model's output did not match its schema |
| `internal` | false | Anything else; see the server's stderr |
| `evals_not_found` | false | No `evals/` directory (set `EVALS_DIR`) |
| `no_eval_results` | false | No eval run recorded yet; the hint gives the command |

## Demo and tests

- [`demo/analyze_pitch_transcript.md`](demo/analyze_pitch_transcript.md): a recorded stdio session (initialize, tools/list, and an `analyze_pitch` call with its progress notifications and structured result) against the live pipeline. Re-record with `python mcp/demoClient.py` (spends credits) or `--url http://127.0.0.1:8765/mcp` for HTTP.
- `backend/tests/test_mcp_server.py` calls every tool through real MCP clients: in-memory sessions with OpenAI and Tavily mocked, a stdio subprocess, and streamable HTTP with the bearer token. Run with `cd backend && pytest tests/test_mcp_server.py`.
