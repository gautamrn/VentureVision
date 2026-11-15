import threading
import time
from collections import deque
from pydantic import BaseModel

from app.schemas.models import RunTelemetry
from app.telemetry.summary import AGENT_NODES


class RunRecord(BaseModel):
    runId: str
    timestamp: float
    durationMs: int
    mode: str
    pitchScore: int | None
    iterations: int
    evidenceCount: int
    status: str
    costUsd: float | None
    promptTokens: int | None
    completionTokens: int | None
    llmCalls: int | None
    searchCalls: int | None
    nodeMs: dict[str, int]
    budgetExitReason: str | None


MAX_RECORDS = 200
_records: deque[RunRecord] = deque(maxlen=MAX_RECORDS)
_lock = threading.Lock()
_totalRuns = 0
_totalErrors = 0


def recordRun(
    *,
    runId: str,
    startTime: float,
    mode: str,
    pitchScore: int | None,
    iterations: int,
    evidenceCount: int,
    telemetry: RunTelemetry | None,
    status: str = "success",
) -> None:
    global _totalRuns, _totalErrors
    record = RunRecord(
        runId=runId,
        timestamp=startTime,
        durationMs=telemetry.duration_ms if telemetry else int((time.time() - startTime) * 1000),
        mode=mode,
        pitchScore=pitchScore,
        iterations=iterations,
        evidenceCount=evidenceCount,
        status=status,
        costUsd=telemetry.total_cost_usd if telemetry else None,
        promptTokens=telemetry.prompt_tokens if telemetry else None,
        completionTokens=telemetry.completion_tokens if telemetry else None,
        llmCalls=telemetry.llm_calls if telemetry else None,
        searchCalls=telemetry.search_calls if telemetry else None,
        nodeMs={n.node: n.total_ms for n in telemetry.nodes} if telemetry else {},
        budgetExitReason=telemetry.budget_exit_reason if telemetry else None,
    )
    with _lock:
        previous = next((r for r in _records if r.runId == runId), None)
        if previous is None:
            _totalRuns += 1
        else:
            _records.remove(previous)
            if previous.status == "error":
                _totalErrors -= 1
        if status == "error":
            _totalErrors += 1
        _records.append(record)


def _average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def getMetrics() -> dict:
    with _lock:
        records = list(_records)
        totalRuns = _totalRuns
        totalErrors = _totalErrors

    successful = [r for r in records if r.status == "success"]
    scores = [r.pitchScore for r in successful if r.pitchScore is not None]
    costed = [r for r in records if r.costUsd is not None]

    modeBreakdown: dict[str, int] = {}
    for r in records:
        modeBreakdown[r.mode] = modeBreakdown.get(r.mode, 0) + 1

    return {
        "totalRuns": totalRuns,
        "totalErrors": totalErrors,
        "avgDurationMs": int(_average([r.durationMs for r in successful])),
        "avgScore": round(_average(scores), 1),
        "avgIterations": round(_average([r.iterations for r in successful]), 1),
        "avgEvidence": round(_average([r.evidenceCount for r in successful]), 1),
        "totalCostUsd": round(sum(r.costUsd for r in costed), 6),
        "avgCostUsd": round(_average([r.costUsd for r in successful if r.costUsd is not None]), 6),
        "avgTokensPerRun": int(
            _average([r.promptTokens + r.completionTokens for r in successful if r.promptTokens is not None])
        ),
        "avgNodeMs": {
            node: int(_average([r.nodeMs[node] for r in successful if node in r.nodeMs]))
            for node in (*AGENT_NODES, "citation_audit")
        },
        "budgetExits": sum(1 for r in records if r.budgetExitReason),
        "modeBreakdown": modeBreakdown,
        "scoreDistribution": {
            "low": sum(1 for s in scores if s < 40),
            "mid": sum(1 for s in scores if 40 <= s < 70),
            "high": sum(1 for s in scores if s >= 70),
        },
        "recentRuns": [r.model_dump() for r in list(reversed(records))[:20]],
    }
