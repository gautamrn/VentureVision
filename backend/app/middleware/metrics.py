import threading
import time
from collections import deque
from pydantic import BaseModel


class RunRecord(BaseModel):
    timestamp: float
    durationMs: int
    mode: str
    pitchScore: int | None
    iterations: int
    evidenceCount: int
    status: str


MAX_RECORDS = 200
_records: deque[RunRecord] = deque(maxlen=MAX_RECORDS)
_lock = threading.Lock()
_totalRuns = 0
_totalErrors = 0


def recordRun(
    startTime: float,
    mode: str,
    pitchScore: int | None,
    iterations: int,
    evidenceCount: int,
    status: str = "success",
) -> None:
    global _totalRuns, _totalErrors
    durationMs = int((time.time() - startTime) * 1000)
    record = RunRecord(
        timestamp=startTime,
        durationMs=durationMs,
        mode=mode,
        pitchScore=pitchScore,
        iterations=iterations,
        evidenceCount=evidenceCount,
        status=status,
    )
    with _lock:
        _records.append(record)
        _totalRuns += 1
        if status == "error":
            _totalErrors += 1


def getMetrics() -> dict:
    with _lock:
        records = list(_records)
        totalRuns = _totalRuns
        totalErrors = _totalErrors

    if not records:
        return {
            "totalRuns": 0,
            "totalErrors": 0,
            "avgDurationMs": 0,
            "avgScore": 0,
            "avgIterations": 0,
            "avgEvidence": 0,
            "modeBreakdown": {},
            "scoreDistribution": {"low": 0, "mid": 0, "high": 0},
            "recentRuns": [],
        }

    successful = [r for r in records if r.status == "success"]
    durations = [r.durationMs for r in successful]
    scores = [r.pitchScore for r in successful if r.pitchScore is not None]
    iterations = [r.iterations for r in successful]
    evidenceCounts = [r.evidenceCount for r in successful]

    modeBreakdown: dict[str, int] = {}
    for r in records:
        modeBreakdown[r.mode] = modeBreakdown.get(r.mode, 0) + 1

    low = sum(1 for s in scores if s < 40)
    mid = sum(1 for s in scores if 40 <= s < 70)
    high = sum(1 for s in scores if s >= 70)

    recentRuns = [r.model_dump() for r in list(reversed(records))[:20]]

    return {
        "totalRuns": totalRuns,
        "totalErrors": totalErrors,
        "avgDurationMs": int(sum(durations) / len(durations)) if durations else 0,
        "avgScore": round(sum(scores) / len(scores), 1) if scores else 0,
        "avgIterations": round(sum(iterations) / len(iterations), 1) if iterations else 0,
        "avgEvidence": round(sum(evidenceCounts) / len(evidenceCounts), 1) if evidenceCounts else 0,
        "modeBreakdown": modeBreakdown,
        "scoreDistribution": {"low": low, "mid": mid, "high": high},
        "recentRuns": recentRuns,
    }
