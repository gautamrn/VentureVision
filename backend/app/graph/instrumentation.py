import time
from typing import Callable

from langchain_core.runnables import RunnableConfig
from langgraph.types import StreamWriter

from app.graph.state import AgentState
from app.schemas.models import NodeTiming
from app.telemetry.collector import NodeCollector, collecting


def instrumentNode(name: str, node: Callable[[AgentState], dict]) -> Callable:
    """Wraps a node so its wall time, LLM token usage, and searches land in the graph state."""

    def run(state: AgentState, config: RunnableConfig, writer: StreamWriter) -> dict:
        collector = NodeCollector(node=name, emit=writer)
        start = time.perf_counter()
        with collecting(collector):
            update = node(state)
        timing = NodeTiming(node=name, duration_ms=round((time.perf_counter() - start) * 1000))
        return {
            **update,
            "llm_calls": collector.llmCalls,
            "search_calls": collector.searchCalls,
            "node_timings": [timing],
        }

    run.__name__ = name
    return run
