"""Connects to the VentureVision MCP server as a client and records a transcript of one analyze_pitch call.

  python mcp/demoClient.py                      spawns the server over stdio
  python mcp/demoClient.py --url http://127.0.0.1:8765/mcp

Runs the real pipeline (spends OpenAI and Tavily credits). Writes mcp/demo/analyze_pitch_transcript.md.
"""

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client

MCP_DIR = Path(__file__).resolve().parent
TRANSCRIPT_PATH = MCP_DIR / "demo" / "analyze_pitch_transcript.md"

SAMPLE_PITCH = (
    "Tablebook: AI bookkeeping for independent restaurants. Restaurants run on 3-5% margins and most owners do their "
    "books in a shoebox. Tablebook connects to Square and Toast, categorizes every transaction, reconciles delivery-app "
    "payouts from DoorDash and Uber Eats, and produces a weekly P&L. The US has over 700,000 restaurants and no "
    "bookkeeping product is built for them. $149 per location per month."
)


def block(value: object) -> str:
    return "```json\n" + json.dumps(value, indent=2, ensure_ascii=False) + "\n```"


async def record(session: ClientSession, transport: str) -> str:
    lines = [f"# MCP transcript: analyze_pitch over {transport}", ""]
    lines.append(f"Recorded {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC by `mcp/demoClient.py` against the live pipeline.")
    lines.append("")

    init = await session.initialize()
    lines += ["## 1. initialize", "", f"Server: `{init.serverInfo.name}`, protocol `{init.protocolVersion}`.", ""]

    tools = (await session.list_tools()).tools
    lines += ["## 2. tools/list", ""]
    for tool in tools:
        lines.append(f"- `{tool.name}`: {(tool.description or '').splitlines()[0]}")
    analyzeTool = next(t for t in tools if t.name == "analyze_pitch")
    lines += ["", "`analyze_pitch` inputSchema:", "", block(analyzeTool.inputSchema), ""]

    arguments = {"pitch_text": SAMPLE_PITCH, "mode": "market_scan"}
    lines += ["## 3. tools/call analyze_pitch", "", "Request arguments:", "", block(arguments), "", "Progress notifications:", ""]
    started = time.perf_counter()

    async def onProgress(progress: float, total: float | None, message: str | None) -> None:
        lines.append(f"- `{time.perf_counter() - started:5.1f}s` progress {progress:g}: {message}")
        print(f"  {message}", file=sys.stderr)

    result = await session.call_tool("analyze_pitch", arguments, progress_callback=onProgress)
    elapsed = time.perf_counter() - started
    lines += ["", f"Result after {elapsed:.1f}s, `isError: {str(result.isError).lower()}`. `structuredContent`:", ""]
    lines += [block(result.structuredContent if result.structuredContent is not None else result.content[0].text), ""]
    return "\n".join(lines)


async def main(url: str | None) -> None:
    if url:
        async with streamablehttp_client(url) as (read, write, _), ClientSession(read, write) as session:
            transcript = await record(session, "streamable HTTP")
    else:
        params = StdioServerParameters(command=sys.executable, args=[str(MCP_DIR / "ventureVisionServer.py")])
        async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            transcript = await record(session, "stdio")
    TRANSCRIPT_PATH.parent.mkdir(exist_ok=True)
    TRANSCRIPT_PATH.write_text(transcript, encoding="utf-8")
    print(f"wrote {TRANSCRIPT_PATH}", file=sys.stderr)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", help="streamable HTTP endpoint; omit to spawn the server over stdio")
    asyncio.run(main(parser.parse_args().url))
