"""VentureVision as an MCP server: pitch analysis, claim verification, and eval scores as agent tools.

  python mcp/ventureVisionServer.py                               stdio (default)
  python mcp/ventureVisionServer.py --transport http --port 8765  streamable HTTP at http://127.0.0.1:8765/mcp

Reads OPENAI_API_KEY and TAVILY_API_KEY from the environment or the repo's .env files.
"""

import argparse
import hmac
import json
import os
import sys
from pathlib import Path
from typing import Annotated, Any, Literal

import anyio
import jsonschema
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

REPO_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_DIR / "backend"))

from app.schemas.evals import LABEL_FOR_VERDICT, DatasetSummary, EvalLabel, EvidenceSnippet, LabelScore, LatestRun  # noqa: E402
from app.schemas.models import Groundedness, Subscores  # noqa: E402

DEFAULT_HTTP_PORT = 8765
MAX_CONCURRENT_ANALYSES = 2
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}

AnalysisMode = Literal["market_scan", "pitch_lab"]
MemoVerdict = Literal["strong", "contradicted", "needs_research", "weak_claim", "vague", "unsubstantiated"]
ErrorCode = Literal[
    "invalid_input",
    "missing_credentials",
    "busy",
    "upstream_unavailable",
    "bad_model_output",
    "internal",
    "evals_not_found",
    "no_eval_results",
]

INSTRUCTIONS = """VentureVision checks startup claims against live web evidence.
- analyze_pitch runs the full multi-agent pipeline (planner, scout, critic, writer, citation audit). It takes 30-90 seconds and spends real OpenAI and Tavily credits, capped per run by RUN_BUDGET_USD.
- verify_claim judges one claim against evidence text you supply. One model call, no web search.
- get_eval_scores returns the latest stored accuracy of the claim verdicts. Free; reads files only.
Errors come back as JSON {"error": {"code", "message", "retryable", "hint"}}. Retry only when retryable is true."""


class ToolFailure(Exception):
    """An error an agent can act on: a stable code, whether retrying can help, and what to do instead."""

    def __init__(self, code: ErrorCode, message: str, *, retryable: bool, hint: str) -> None:
        super().__init__(message)
        self.code, self.message, self.retryable, self.hint = code, message, retryable, hint

    def __str__(self) -> str:
        return json.dumps(
            {"error": {"code": self.code, "message": self.message, "retryable": self.retryable, "hint": self.hint}}
        )


class VerdictCounts(BaseModel):
    strong: int
    contradicted: int
    needs_research: int
    weak_claim: int
    vague: int
    unsubstantiated: int


class LabelCounts(BaseModel):
    supported: int
    unsupported: int
    contradicted: int


class ClaimVerdict(BaseModel):
    excerpt: str
    verdict: MemoVerdict
    eval_label: EvalLabel
    note: str
    evidence_quote: str | None
    source_url: str | None
    downgraded_from: MemoVerdict | None


class Competitor(BaseModel):
    name: str
    pricing: str
    funding: str
    source_url: str | None


class RunStats(BaseModel):
    duration_ms: int
    llm_calls: int
    search_calls: int
    failed_searches: int
    total_cost_usd: float
    budget_usd: float
    budget_exit_reason: str | None
    models: list[str]


class PitchAnalysis(BaseModel):
    mode: AnalysisMode
    pitch_score: int
    subscores: Subscores
    executive_summary: str
    verdict_counts: VerdictCounts
    label_counts: LabelCounts
    groundedness: Groundedness | None
    claims: list[ClaimVerdict]
    competitors: list[Competitor]
    risks: list[str]
    investor_questions: list[str]
    sources_consulted: int
    run: RunStats


class ClaimCheck(BaseModel):
    verdict: EvalLabel
    reasoning: str
    evidence_quote: str | None
    downgraded_from: EvalLabel | None
    model: str
    cost_usd: float


class ScoreCard(BaseModel):
    verifier: str
    model: str | None
    run_id: str
    run_at: str
    overall_accuracy: float
    correct: int
    case_count: int
    labels: list[LabelScore]
    misses: int
    cost_usd: float


class EvalScores(BaseModel):
    measures: str
    dataset: DatasetSummary
    heuristic_baseline: ScoreCard | None
    llm_verifier: ScoreCard | None
    ci_gate: str | None
    stored_runs: int


def requireKeys(*names: str) -> None:
    missing = [name for name in names if not os.getenv(name)]
    if missing:
        raise ToolFailure(
            "missing_credentials",
            f"The server has no {' or '.join(missing)} configured.",
            retryable=False,
            hint="Set the key in the MCP server's env block or in the repo's .env, then restart the server.",
        )


def failureFromNode(kind: str, message: str) -> ToolFailure:
    if kind == "upstream_api":
        return ToolFailure("upstream_unavailable", message, retryable=True, hint="An upstream API failed; retry in a minute.")
    if kind == "bad_model_output":
        return ToolFailure("bad_model_output", message, retryable=True, hint="The model returned malformed output; retrying usually works.")
    return ToolFailure("internal", message, retryable=False, hint="Check the MCP server's stderr log.")


def countVerdicts(verdicts: list[str]) -> tuple[VerdictCounts, LabelCounts]:
    memoCounts = {name: 0 for name in VerdictCounts.model_fields}
    labelCounts = {name: 0 for name in LabelCounts.model_fields}
    for verdict in verdicts:
        memoCounts[verdict] += 1
        labelCounts[LABEL_FOR_VERDICT[verdict]] += 1
    return VerdictCounts(**memoCounts), LabelCounts(**labelCounts)


def runAnalysis(pitch: str, mode: AnalysisMode, onNode: Any) -> PitchAnalysis:
    import time

    from app.routers.analyze import buildInitialState, runToCompletion

    start = time.perf_counter()
    state = buildInitialState(pitch, mode)
    accumulator, memo, failure = runToCompletion(state, onNode)
    if failure is not None:
        raise failureFromNode(failure.kind, failure.message)
    if memo is None:
        raise ToolFailure("internal", "The pipeline finished without a memo.", retryable=False, hint="Check the MCP server's stderr log.")

    telemetry = accumulator.summarize(round((time.perf_counter() - start) * 1000), state["budget_usd"])
    verdictCounts, labelCounts = countVerdicts([a.annotation_type for a in memo.pitch_annotations])
    return PitchAnalysis(
        mode=mode,
        pitch_score=memo.pitch_score,
        subscores=memo.subscores,
        executive_summary=memo.executive_summary,
        verdict_counts=verdictCounts,
        label_counts=labelCounts,
        groundedness=memo.groundedness,
        claims=[
            ClaimVerdict(
                excerpt=a.excerpt,
                verdict=a.annotation_type,
                eval_label=LABEL_FOR_VERDICT[a.annotation_type],
                note=a.note,
                evidence_quote=a.citation.quote if a.citation else None,
                source_url=str(a.citation.source_url) if a.citation else None,
                downgraded_from=a.downgraded_from,
            )
            for a in memo.pitch_annotations
        ],
        competitors=[
            Competitor(
                name=c.competitor,
                pricing=c.pricing,
                funding=c.funding,
                source_url=str(c.citation.source_url) if c.citation else None,
            )
            for c in memo.market_matrix
        ],
        risks=memo.risk_vectors,
        investor_questions=[q.question for q in memo.investor_questions],
        sources_consulted=len(memo.citation_links),
        run=RunStats(
            duration_ms=telemetry.duration_ms,
            llm_calls=telemetry.llm_calls,
            search_calls=telemetry.search_calls,
            failed_searches=telemetry.failed_searches,
            total_cost_usd=telemetry.total_cost_usd,
            budget_usd=telemetry.budget_usd,
            budget_exit_reason=telemetry.budget_exit_reason,
            models=sorted({c.model for c in accumulator.llmCalls}),
        ),
    )


def scoreCard(run: LatestRun | None, verifier: str) -> ScoreCard | None:
    if run is None:
        return None
    return ScoreCard(
        verifier=verifier,
        model=run.model,
        run_id=run.run_id,
        run_at=run.started_at.isoformat(),
        overall_accuracy=run.overall_accuracy,
        correct=sum(s.correct for s in run.labels),
        case_count=run.case_count,
        labels=run.labels,
        misses=len(run.failures),
        cost_usd=run.cost_usd,
    )


class VentureVisionMcp(FastMCP):
    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        tool = self._tool_manager.get_tool(name)
        if tool is not None:
            # FastMCP skips JSON Schema validation and its argument models ignore unknown keys.
            try:
                jsonschema.validate(arguments, tool.parameters)
            except jsonschema.ValidationError as exc:
                raise ToolFailure(
                    "invalid_input",
                    f"{name}: {exc.message}",
                    retryable=False,
                    hint="Fix the arguments to match the tool's inputSchema.",
                ) from None
        try:
            return await super().call_tool(name, arguments)
        except ToolError as exc:
            # FastMCP prefixes every tool exception with "Error executing tool ..."; agents get bare JSON instead.
            if isinstance(exc.__cause__, ToolFailure):
                raise exc.__cause__ from None
            raise


def buildServer(host: str = "127.0.0.1", port: int = DEFAULT_HTTP_PORT) -> FastMCP:
    server = VentureVisionMcp("venture-vision", instructions=INSTRUCTIONS, host=host, port=port)
    analysisSlots = anyio.CapacityLimiter(MAX_CONCURRENT_ANALYSES)

    @server.tool(
        name="analyze_pitch",
        title="Analyze a startup pitch",
        annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True, idempotentHint=False),
    )
    async def analyzePitch(
        pitch_text: Annotated[str, Field(min_length=40, max_length=5000, description="The pitch or idea, 40-5000 characters.")],
        ctx: Context,
        mode: Annotated[
            AnalysisMode,
            Field(description="market_scan: is this worth building, who else does it. pitch_lab: how investor-ready is this text."),
        ] = "market_scan",
    ) -> PitchAnalysis:
        """Research a startup pitch on the live web and return the memo summary with a verdict for every claim.

        Each claim gets strong / contradicted / needs_research (market_scan) or strong / contradicted / weak_claim /
        vague / unsubstantiated (pitch_lab); strong and contradicted always carry a verbatim evidence quote and URL.
        Spends OpenAI and Tavily credits; takes 30-90 seconds."""
        pitch = pitch_text.strip()
        if len(pitch) < 40:
            raise ToolFailure("invalid_input", "pitch_text is under 40 characters once whitespace is trimmed.", retryable=False, hint="Send the full pitch text.")
        requireKeys("OPENAI_API_KEY", "TAVILY_API_KEY")
        if analysisSlots.available_tokens == 0:
            raise ToolFailure(
                "busy",
                f"{MAX_CONCURRENT_ANALYSES} analyses are already running on this server.",
                retryable=True,
                hint="Retry after about a minute.",
            )

        finishedNodes = 0

        def onNode(node: str) -> None:
            nonlocal finishedNodes
            finishedNodes += 1
            anyio.from_thread.run(ctx.report_progress, finishedNodes, None, f"{node} finished")

        async with analysisSlots:
            return await anyio.to_thread.run_sync(runAnalysis, pitch, mode, onNode)

    @server.tool(
        name="verify_claim",
        title="Verify one claim against evidence",
        annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False, idempotentHint=True),
    )
    async def verifyClaimTool(
        claim: Annotated[str, Field(min_length=3, max_length=1000, description="One factual claim, e.g. a sentence from a pitch.")],
        evidence_text: Annotated[
            str, Field(min_length=1, max_length=20000, description="The evidence to judge it against, e.g. an article excerpt.")
        ],
    ) -> ClaimCheck:
        """Judge one claim against the evidence you supply: supported, unsupported, or contradicted.

        Uses the pipeline's verdict rules: a supported or contradicted verdict must quote the evidence verbatim, or it is
        downgraded to unsupported. Missing evidence is never a contradiction. One model call, no web search."""
        if not claim.strip() or not evidence_text.strip():
            raise ToolFailure("invalid_input", "claim and evidence_text must contain text.", retryable=False, hint="Send non-blank strings.")
        requireKeys("OPENAI_API_KEY")

        from app.graph.errors import describeFailure
        from app.verification.claimVerifier import verifyClaim

        evidence = [EvidenceSnippet(source_url=None, title="Evidence supplied by the caller", text=evidence_text)]
        try:
            result = await anyio.to_thread.run_sync(verifyClaim, claim.strip(), evidence)
        except Exception as exc:
            kind, message = describeFailure("verifier", exc)
            raise failureFromNode(kind, message) from exc
        return ClaimCheck(
            verdict=result.verdict,
            reasoning=result.reasoning,
            evidence_quote=result.citation.quote if result.citation else None,
            downgraded_from=result.downgraded_from,
            model=result.model,
            cost_usd=result.cost_usd,
        )

    @server.tool(
        name="get_eval_scores",
        title="Latest eval scores",
        annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False, idempotentHint=True),
    )
    def getEvalScores() -> EvalScores:
        """Latest stored accuracy of VentureVision's claim verdicts on its hand-labeled dataset, per label.

        Reports the model-free heuristic baseline and the LLM verifier separately; either is null if never run."""
        from app.evals.results import buildSummary

        try:
            summary = buildSummary()
        except FileNotFoundError as exc:
            raise ToolFailure(
                "evals_not_found",
                f"Eval files not found ({exc.filename}).",
                retryable=False,
                hint="Run the server from a VentureVision checkout, or set EVALS_DIR to its evals/ directory.",
            ) from exc
        if summary.latest_heuristic is None and summary.latest_llm is None:
            raise ToolFailure(
                "no_eval_results",
                "No eval run has been recorded yet.",
                retryable=False,
                hint="Run: python evals/run_evals.py --mode heuristic --publish",
            )
        return EvalScores(
            measures=(
                "Accuracy of claim verdicts (supported / unsupported / contradicted) against hand-assigned labels, "
                "given fixed evidence. Does not measure web retrieval."
            ),
            dataset=summary.dataset,
            heuristic_baseline=scoreCard(summary.latest_heuristic, "Heuristic baseline (no model)"),
            llm_verifier=scoreCard(summary.latest_llm, "LLM verifier (pipeline verdict rules)"),
            ci_gate=(
                f"CI fails if heuristic accuracy drops more than 3 points below {summary.baseline.overall_accuracy}%."
                if summary.baseline
                else None
            ),
            stored_runs=len(summary.history),
        )

    for tool in server._tool_manager.list_tools():
        tool.parameters["additionalProperties"] = False

    return server


class BearerTokenMiddleware:
    def __init__(self, app: Any, token: str) -> None:
        self.app, self.expected = app, f"Bearer {token}".encode()

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope["type"] == "http":
            supplied = dict(scope.get("headers") or []).get(b"authorization", b"")
            if not hmac.compare_digest(supplied, self.expected):
                await send({"type": "http.response.start", "status": 401, "headers": [(b"content-type", b"application/json")]})
                await send({"type": "http.response.body", "body": b'{"error": "missing or wrong bearer token"}'})
                return
        await self.app(scope, receive, send)


def httpApp(server: FastMCP, token: str | None) -> Any:
    app = server.streamable_http_app()
    return BearerTokenMiddleware(app, token) if token else app


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=DEFAULT_HTTP_PORT)
    args = parser.parse_args(argv)

    from dotenv import load_dotenv

    load_dotenv(REPO_DIR / ".env")
    load_dotenv(REPO_DIR / "backend" / ".env")

    server = buildServer(args.host, args.port)
    if args.transport == "stdio":
        server.run("stdio")
        return 0

    token = os.getenv("VV_MCP_HTTP_TOKEN")
    if args.host not in LOOPBACK_HOSTS and not token:
        print("Refusing to serve analyze_pitch beyond localhost without VV_MCP_HTTP_TOKEN set.", file=sys.stderr)
        return 2
    import uvicorn

    print(f"VentureVision MCP on http://{args.host}:{args.port}{server.settings.streamable_http_path}", file=sys.stderr)
    uvicorn.run(httpApp(server, token), host=args.host, port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
