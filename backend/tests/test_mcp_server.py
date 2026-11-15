"""The MCP server, exercised only through MCP clients: in-memory sessions, a stdio subprocess, and streamable HTTP."""

import json
import os
import shutil
import sys
import threading
import time

import httpx
import pytest
import uvicorn
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client
from mcp.shared.memory import create_connected_server_and_client_session

from app.evals.dataset import REPO_DIR
from tests.fakes import SAMPLE_PITCH, annotationDraft, competitorDraft, critique, memoSynthesis, researchPlan

SERVER_SCRIPT = REPO_DIR / "mcp" / "ventureVisionServer.py"
sys.path.insert(0, str(SERVER_SCRIPT.parent))

import ventureVisionServer as vv  # noqa: E402

pytestmark = pytest.mark.anyio

DEVOPS_EVIDENCE = "Grand View Research: DevOps Market Size Worth $12.85 Billion by 2025 | CAGR: 18.60%."


@pytest.fixture
def anyio_backend():
    return "asyncio"


def errorOf(result) -> dict:
    assert result.isError
    return json.loads(result.content[0].text)["error"]


def scriptPipeline(fakeOpenAI) -> None:
    fakeOpenAI.script("ResearchPlan", researchPlan(["rover funding", "dog walking market size"]))
    fakeOpenAI.script("CritiqueResult", critique(0.9, True))
    fakeOpenAI.script(
        "MemoSynthesis",
        memoSynthesis(
            annotations=[
                annotationDraft("strong", "vetted local walkers", 1, "Evidence about rover funding."),
                annotationDraft("contradicted", "no direct competitors", 2, "Evidence about dog walking market size."),
                annotationDraft("strong", "20% commission per walk", 1, "Rover is profitable."),
            ],
            competitors=[competitorDraft("Rover", 1, "Evidence about rover funding.")],
        ),
    )


async def callInMemory(name: str, arguments: dict, progress: list | None = None):
    async with create_connected_server_and_client_session(vv.buildServer()._mcp_server) as client:
        async def onProgress(value, total, message):
            if progress is not None:
                progress.append(message)

        return await client.call_tool(name, arguments, progress_callback=onProgress)


# Discovery: strict input schemas and declared output schemas


async def testToolsDeclareStrictInputAndStructuredOutputSchemas():
    async with create_connected_server_and_client_session(vv.buildServer()._mcp_server) as client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}

    assert set(tools) == {"analyze_pitch", "verify_claim", "get_eval_scores"}
    assert all(t.inputSchema["additionalProperties"] is False and t.outputSchema for t in tools.values())
    analyze = tools["analyze_pitch"].inputSchema
    assert analyze["required"] == ["pitch_text"]
    assert (analyze["properties"]["pitch_text"]["minLength"], analyze["properties"]["pitch_text"]["maxLength"]) == (40, 5000)
    assert analyze["properties"]["mode"]["enum"] == ["market_scan", "pitch_lab"]
    assert tools["verify_claim"].inputSchema["required"] == ["claim", "evidence_text"]
    assert tools["analyze_pitch"].annotations.openWorldHint is True


# analyze_pitch


async def testAnalyzePitchReturnsMemoSummaryVerdictCountsAndProgress(fakeOpenAI, fakeTavily):
    scriptPipeline(fakeOpenAI)
    progress: list[str] = []

    result = await callInMemory("analyze_pitch", {"pitch_text": SAMPLE_PITCH, "mode": "market_scan"}, progress)

    assert not result.isError
    analysis = vv.PitchAnalysis.model_validate(result.structuredContent)
    assert analysis.verdict_counts.model_dump() == {
        "strong": 1, "contradicted": 1, "needs_research": 1, "weak_claim": 0, "vague": 0, "unsubstantiated": 0,
    }
    assert analysis.label_counts.model_dump() == {"supported": 1, "unsupported": 1, "contradicted": 1}
    assert analysis.groundedness.model_dump() == {"cited_claims": 3, "total_claims": 4, "downgraded_claims": 1}
    downgraded = analysis.claims[2]
    assert (downgraded.verdict, downgraded.downgraded_from, downgraded.source_url) == ("needs_research", "strong", None)
    assert analysis.claims[1].source_url == "https://example.com/dog-walking-market-size"
    assert analysis.run.models == ["gpt-4o-mini"] and analysis.run.total_cost_usd > 0
    assert progress == [f"{node} finished" for node in ("planner", "scout", "critic", "writer", "citation_audit")]


@pytest.mark.parametrize(
    "arguments, expected",
    [
        ({"pitch_text": "too short"}, "is too short"),
        ({"pitch_text": SAMPLE_PITCH, "mode": "deep_dive"}, "is not one of"),
        ({"pitch_text": SAMPLE_PITCH, "budget": 5}, "Additional properties are not allowed"),
    ],
    ids=["short-pitch", "unknown-mode", "unknown-argument"],
)
async def testAnalyzePitchRejectsInvalidInputBeforeRunning(fakeOpenAI, arguments, expected):
    error = errorOf(await callInMemory("analyze_pitch", arguments))

    assert (error["code"], error["retryable"]) == ("invalid_input", False)
    assert expected in error["message"]
    assert fakeOpenAI.calls == []


async def testAnalyzePitchReportsUpstreamOutageAsRetryable(fakeOpenAI, fakeTavily):
    fakeOpenAI.script("ResearchPlan", researchPlan(["rover funding"]))
    fakeTavily.failAll = True

    error = errorOf(await callInMemory("analyze_pitch", {"pitch_text": SAMPLE_PITCH}))

    assert (error["code"], error["retryable"]) == ("upstream_unavailable", True)
    assert error["message"].startswith("Web search failed")


async def testAnalyzePitchWithoutKeysTellsTheAgentWhatToConfigure(monkeypatch, fakeOpenAI):
    monkeypatch.delenv("TAVILY_API_KEY")

    error = errorOf(await callInMemory("analyze_pitch", {"pitch_text": SAMPLE_PITCH}))

    assert (error["code"], error["retryable"]) == ("missing_credentials", False)
    assert "TAVILY_API_KEY" in error["message"] and "env" in error["hint"]


# verify_claim


async def testVerifyClaimReturnsVerdictWithVerbatimQuote(fakeOpenAI):
    fakeOpenAI.script(
        "ClaimVerdictDraft",
        {"verdict": "supported", "evidence_ref": 1, "evidence_quote": "DevOps Market Size Worth $12.85 Billion by 2025", "reasoning": "$12.85B is over $10B."},
    )

    result = await callInMemory("verify_claim", {"claim": "The DevOps market is worth over $10B.", "evidence_text": DEVOPS_EVIDENCE})

    check = vv.ClaimCheck.model_validate(result.structuredContent)
    assert (check.verdict, check.evidence_quote, check.model) == ("supported", "DevOps Market Size Worth $12.85 Billion by 2025", "gpt-4o-mini")


async def testVerifyClaimDowngradesAContradictionItCannotQuote(fakeOpenAI):
    fakeOpenAI.script(
        "ClaimVerdictDraft",
        {"verdict": "contradicted", "evidence_ref": 1, "evidence_quote": "The market is shrinking.", "reasoning": "It shrinks."},
    )

    result = await callInMemory("verify_claim", {"claim": "The DevOps market is growing.", "evidence_text": DEVOPS_EVIDENCE})

    check = vv.ClaimCheck.model_validate(result.structuredContent)
    assert (check.verdict, check.downgraded_from, check.evidence_quote) == ("unsupported", "contradicted", None)


async def testVerifyClaimRejectsBlankEvidence(fakeOpenAI):
    error = errorOf(await callInMemory("verify_claim", {"claim": "The market is big.", "evidence_text": "   "}))

    assert error["code"] == "invalid_input"
    assert fakeOpenAI.calls == []


# get_eval_scores


async def testGetEvalScoresReportsStoredBaselineAndUnrunLlmMode():
    from app.evals.results import buildSummary

    expected = buildSummary()

    result = await callInMemory("get_eval_scores", {})

    scores = vv.EvalScores.model_validate(result.structuredContent)
    assert scores.dataset.case_count == expected.dataset.case_count
    assert scores.heuristic_baseline.overall_accuracy == expected.latest_heuristic.overall_accuracy
    assert scores.heuristic_baseline.misses == len(expected.latest_heuristic.failures)
    assert (scores.llm_verifier is None) == (expected.latest_llm is None)
    assert "Does not measure web retrieval" in scores.measures


async def testGetEvalScoresWithNoRecordedRunsSaysHowToProduceOne(tmp_path, monkeypatch):
    for name in ("golden_dataset.jsonl", "dataset.json"):
        shutil.copy(REPO_DIR / "evals" / name, tmp_path / name)
    monkeypatch.setenv("EVALS_DIR", str(tmp_path))

    error = errorOf(await callInMemory("get_eval_scores", {}))

    assert error["code"] == "no_eval_results" and "run_evals.py" in error["hint"]


# Real transports


async def testStdioTransport():
    env = {**os.environ, "OPENAI_API_KEY": "", "TAVILY_API_KEY": "", "PYTHONIOENCODING": "utf-8"}
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER_SCRIPT)], env=env)

    async with stdio_client(params) as (read, write), ClientSession(read, write) as client:
        init = await client.initialize()
        scores = await client.call_tool("get_eval_scores", {})
        noKeys = await client.call_tool("verify_claim", {"claim": "The market is big.", "evidence_text": DEVOPS_EVIDENCE})

    assert init.serverInfo.name == "venture-vision"
    assert vv.EvalScores.model_validate(scores.structuredContent).heuristic_baseline is not None
    assert errorOf(noKeys)["code"] == "missing_credentials"


@pytest.fixture
def httpServerUrl():
    config = uvicorn.Config(vv.httpApp(vv.buildServer(), token="test-mcp-token"), host="127.0.0.1", port=0, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.01)
    yield f"http://127.0.0.1:{server.servers[0].sockets[0].getsockname()[1]}/mcp"
    server.should_exit = True
    thread.join(timeout=5)


async def testStreamableHttpTransportRequiresTokenAndRunsAnalysis(httpServerUrl, fakeOpenAI, fakeTavily):
    scriptPipeline(fakeOpenAI)
    async with httpx.AsyncClient() as http:
        unauthorized = await http.post(httpServerUrl, json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})

    headers = {"Authorization": "Bearer test-mcp-token"}
    async with streamablehttp_client(httpServerUrl, headers=headers) as (read, write, _), ClientSession(read, write) as client:
        await client.initialize()
        result = await client.call_tool("analyze_pitch", {"pitch_text": SAMPLE_PITCH, "mode": "pitch_lab"})

    assert unauthorized.status_code == 401
    analysis = vv.PitchAnalysis.model_validate(result.structuredContent)
    assert analysis.mode == "pitch_lab" and analysis.label_counts.contradicted == 1
