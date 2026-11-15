import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from langchain_core.runnables import RunnableConfig

from app.graph.errors import NodeFailure, RunCancelled
from app.graph.state import AgentState
from app.schemas.models import NodeTiming
from app.telemetry.collector import NodeCollector, collecting


@dataclass
class RunControl:
    """Per-run handle shared with the nodes: a cancel flag the API can set, and a progress sink.

    Progress goes straight to the client instead of through LangGraph's custom stream, which
    drops a node's events when that node later raises (exactly when "search failed" matters).
    """

    cancelEvent: threading.Event = field(default_factory=threading.Event)
    emit: Callable[[dict[str, Any]], None] = lambda _: None

    def cancel(self) -> None:
        self.cancelEvent.set()

    @property
    def cancelled(self) -> bool:
        return self.cancelEvent.is_set()


def runControlFrom(config: RunnableConfig) -> RunControl:
    return (config.get("configurable") or {}).get("runControl") or RunControl()


def instrumentNode(name: str, node: Callable[[AgentState], dict]) -> Callable:
    """Wraps a node with timing, LLM/search telemetry, cooperative cancellation, and failure attribution."""

    def run(state: AgentState, config: RunnableConfig) -> dict:
        control = runControlFrom(config)
        if control.cancelled:
            raise RunCancelled(name, started=False)

        collector = NodeCollector(node=name, emit=control.emit, isCancelled=lambda: control.cancelled)
        start = time.perf_counter()

        def elapsed() -> int:
            return round((time.perf_counter() - start) * 1000)

        with collecting(collector):
            try:
                update = node(state)
            except RunCancelled as exc:
                exc.llmCalls, exc.searchCalls, exc.durationMs = collector.llmCalls, collector.searchCalls, elapsed()
                raise
            except Exception as exc:
                raise NodeFailure(name, exc, collector.llmCalls, collector.searchCalls, elapsed()) from exc

        return {
            **update,
            "llm_calls": collector.llmCalls,
            "search_calls": collector.searchCalls,
            "node_timings": [NodeTiming(node=name, duration_ms=elapsed())],
        }

    run.__name__ = name
    return run
