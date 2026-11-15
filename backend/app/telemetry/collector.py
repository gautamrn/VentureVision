from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator

from app.schemas.models import LlmCall, SearchCall


@dataclass
class NodeCollector:
    """Telemetry and progress for one node execution, reachable from inside the node via a contextvar."""

    node: str
    emit: Callable[[dict[str, Any]], None] = lambda _: None
    isCancelled: Callable[[], bool] = lambda: False
    llmCalls: list[LlmCall] = field(default_factory=list)
    searchCalls: list[SearchCall] = field(default_factory=list)


_current: ContextVar[NodeCollector | None] = ContextVar("nodeCollector", default=None)


def currentCollector() -> NodeCollector:
    # Nodes called outside the graph (unit tests, scripts) record into a throwaway collector.
    return _current.get() or NodeCollector(node="standalone")


@contextmanager
def collecting(collector: NodeCollector) -> Iterator[NodeCollector]:
    token = _current.set(collector)
    try:
        yield collector
    finally:
        _current.reset(token)
