from dataclasses import dataclass, field
from typing import Any

from app.schemas.models import LlmCall, NodeLatency, NodeTiming, RunTelemetry, SearchCall
from app.telemetry.pricing import PRICING

AGENT_NODES = ("planner", "scout", "critic", "writer")


def summarizeRun(
    *,
    llmCalls: list[LlmCall],
    searchCalls: list[SearchCall],
    nodeTimings: list[NodeTiming],
    durationMs: int,
    budgetUsd: float,
    budgetExitReason: str | None,
) -> RunTelemetry:
    latencies: dict[str, NodeLatency] = {}
    for timing in nodeTimings:
        latency = latencies.setdefault(timing.node, NodeLatency(node=timing.node, runs=0, total_ms=0))
        latency.runs += 1
        latency.total_ms += timing.duration_ms

    llmCostUsd = sum(c.cost_usd for c in llmCalls)
    searchCostUsd = sum(c.cost_usd for c in searchCalls)
    return RunTelemetry(
        agent_count=sum(1 for node in AGENT_NODES if node in latencies),
        duration_ms=durationMs,
        llm_calls=len(llmCalls),
        prompt_tokens=sum(c.prompt_tokens for c in llmCalls),
        completion_tokens=sum(c.completion_tokens for c in llmCalls),
        search_calls=len(searchCalls),
        failed_searches=sum(1 for c in searchCalls if c.error),
        llm_cost_usd=round(llmCostUsd, 6),
        search_cost_usd=round(searchCostUsd, 6),
        total_cost_usd=round(llmCostUsd + searchCostUsd, 6),
        budget_usd=budgetUsd,
        budget_exit_reason=budgetExitReason,
        nodes=list(latencies.values()),
        pricing_as_of=PRICING.as_of,
    )


@dataclass
class RunAccumulator:
    """Folds streamed node updates into the totals a run's telemetry and metrics need."""

    llmCalls: list[LlmCall] = field(default_factory=list)
    searchCalls: list[SearchCall] = field(default_factory=list)
    nodeTimings: list[NodeTiming] = field(default_factory=list)
    budgetExitReason: str | None = None
    iterations: int = 0
    evidenceCount: int = 0
    pitchScore: int | None = None

    def apply(self, update: dict[str, Any]) -> None:
        self.llmCalls.extend(update.get("llm_calls", []))
        self.searchCalls.extend(update.get("search_calls", []))
        self.nodeTimings.extend(update.get("node_timings", []))
        if update.get("budget_exit_reason"):
            self.budgetExitReason = update["budget_exit_reason"]
        if "analysis_iteration" in update:
            self.iterations = update["analysis_iteration"]
        if "raw_evidence" in update:
            self.evidenceCount = len(update["raw_evidence"])
        memo = update.get("final_memo")
        if memo is not None:
            self.pitchScore = memo.pitch_score

    def summarize(self, durationMs: int, budgetUsd: float) -> RunTelemetry:
        return summarizeRun(
            llmCalls=self.llmCalls,
            searchCalls=self.searchCalls,
            nodeTimings=self.nodeTimings,
            durationMs=durationMs,
            budgetUsd=budgetUsd,
            budgetExitReason=self.budgetExitReason,
        )
