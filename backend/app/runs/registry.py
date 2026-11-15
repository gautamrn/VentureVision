import secrets
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Literal

from app.graph.instrumentation import RunControl
from app.schemas.models import RunTelemetry
from app.telemetry.summary import RunAccumulator

MAX_ACTIVE_RUNS = 5
MAX_RETRIES = 2
FAILED_RUN_TTL_SECONDS = 30 * 60

RunStatus = Literal["running", "failed", "succeeded", "cancelled"]


class RunBusyError(RuntimeError):
    pass


class RunStateError(RuntimeError):
    pass


@dataclass
class RunHandle:
    runId: str
    mode: str
    budgetUsd: float
    startedAt: float = field(default_factory=time.time)
    control: RunControl = field(default_factory=RunControl)
    accumulator: RunAccumulator = field(default_factory=RunAccumulator)
    status: RunStatus = "running"
    attempt: int = 1
    retryable: bool = False
    failedNode: str | None = None
    finishedAt: float | None = None
    completedAttemptsMs: int = 0
    attemptStartedAt: float = field(default_factory=time.perf_counter)

    @property
    def retriesLeft(self) -> int:
        return MAX_RETRIES - (self.attempt - 1)

    def elapsedMs(self) -> int:
        return self.completedAttemptsMs + round((time.perf_counter() - self.attemptStartedAt) * 1000)

    def telemetry(self) -> RunTelemetry:
        return self.accumulator.summarize(self.elapsedMs(), self.budgetUsd)


class RunRegistry:
    """In-process run table: live runs, plus failed runs kept for a while so they can be retried.

    A run counts against MAX_ACTIVE_RUNS until its worker thread finishes, including a cancelled
    run that is still waiting for an in-flight API call to return.
    """

    def __init__(self, onForget: Callable[[str], None]) -> None:
        self._runs: dict[str, RunHandle] = {}
        self._lock = threading.Lock()
        self._active = 0
        self._onForget = onForget

    @property
    def activeCount(self) -> int:
        with self._lock:
            return self._active

    def start(self, mode: str, budgetUsd: float) -> RunHandle:
        self.sweep()
        with self._lock:
            if self._active >= MAX_ACTIVE_RUNS:
                raise RunBusyError("Server busy. Try again in a minute.")
            handle = RunHandle(runId=secrets.token_urlsafe(16), mode=mode, budgetUsd=budgetUsd)
            self._runs[handle.runId] = handle
            self._active += 1
            return handle

    def get(self, runId: str) -> RunHandle | None:
        with self._lock:
            return self._runs.get(runId)

    def resume(self, runId: str) -> RunHandle:
        self.sweep()
        with self._lock:
            handle = self._runs.get(runId)
            if handle is None:
                raise KeyError(runId)
            if handle.status != "failed" or not handle.retryable:
                raise RunStateError(f"Run is {handle.status} and cannot be retried.")
            if handle.retriesLeft <= 0:
                raise RunStateError("This run has used all its retries. Start a new analysis.")
            if self._active >= MAX_ACTIVE_RUNS:
                raise RunBusyError("Server busy. Try again in a minute.")
            handle.status = "running"
            handle.attempt += 1
            handle.control = RunControl()
            handle.attemptStartedAt = time.perf_counter()
            self._active += 1
            return handle

    def finish(self, handle: RunHandle, status: RunStatus, retryable: bool = False) -> None:
        with self._lock:
            handle.completedAttemptsMs += round((time.perf_counter() - handle.attemptStartedAt) * 1000)
            handle.status = status
            handle.retryable = retryable and handle.retriesLeft > 0
            handle.finishedAt = time.time()
            self._active -= 1
            forget = not handle.retryable
            if forget:
                self._runs.pop(handle.runId, None)
        if forget:
            self._onForget(handle.runId)

    def sweep(self) -> None:
        cutoff = time.time() - FAILED_RUN_TTL_SECONDS
        with self._lock:
            expired = [
                runId
                for runId, h in self._runs.items()
                if h.status == "failed" and h.finishedAt is not None and h.finishedAt < cutoff
            ]
            for runId in expired:
                del self._runs[runId]
        for runId in expired:
            self._onForget(runId)
