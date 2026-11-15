import logging
from typing import Any, Callable

from app.graph.errors import NodeFailure, RunCancelled
from app.graph.workflow import resumableGraph
from app.middleware.metrics import recordRun
from app.runs.events import serializeNodeOutput
from app.runs.registry import RunHandle, RunRegistry, RunStatus

logger = logging.getLogger(__name__)

Emit = Callable[[str, dict[str, Any]], None]

METRIC_STATUS: dict[RunStatus, str] = {"succeeded": "success", "failed": "error", "cancelled": "cancelled"}

registry = RunRegistry(onForget=resumableGraph.checkpointer.delete_thread)


def executeAttempt(handle: RunHandle, graphInput: dict | None, emit: Emit) -> None:
    """Runs one attempt on the calling thread. graphInput=None resumes from the run's last checkpoint."""
    def emitProgress(payload: dict[str, Any]) -> None:
        payload = dict(payload)
        emit(payload.pop("type"), payload)

    handle.control.emit = emitProgress
    config = {"configurable": {"thread_id": handle.runId, "runControl": handle.control}}
    status: RunStatus = "failed"
    retryable = False
    try:
        for chunk in resumableGraph.stream(graphInput, config, stream_mode="updates"):
            for nodeName, update in chunk.items():
                handle.accumulator.apply(update)
                if nodeName == "citation_audit" and update.get("final_memo") is not None:
                    memo = update["final_memo"].model_copy(update={"telemetry": handle.telemetry()})
                    update = {**update, "final_memo": memo}
                emit(nodeName, serializeNodeOutput(nodeName, update))
        status = "succeeded"
    except RunCancelled as exc:
        if exc.started:
            handle.accumulator.addPartial(exc.node, exc.llmCalls, exc.searchCalls, exc.durationMs)
        status = "cancelled"
        emit("cancelled", {"runId": handle.runId, "node": exc.node})
    except NodeFailure as exc:
        handle.accumulator.addPartial(exc.node, exc.llmCalls, exc.searchCalls, exc.durationMs)
        handle.failedNode = exc.node
        retryable = True
        logger.warning("run %s failed in %s: %r", handle.runId, exc.node, exc.cause)
        emit(
            "error",
            {
                "message": exc.message,
                "node": exc.node,
                "kind": exc.kind,
                "retryable": handle.retriesLeft > 0,
                "runId": handle.runId,
            },
        )
    except Exception as exc:
        logger.exception("run %s failed outside any node", handle.runId)
        emit(
            "error",
            {
                "message": f"The pipeline failed unexpectedly ({type(exc).__name__}).",
                "node": None,
                "kind": "internal",
                "retryable": False,
                "runId": handle.runId,
            },
        )
    finally:
        telemetry = handle.telemetry()
        registry.finish(handle, status, retryable)
        recordRun(
            runId=handle.runId,
            startTime=handle.startedAt,
            mode=handle.mode,
            pitchScore=handle.accumulator.pitchScore,
            iterations=handle.accumulator.iterations,
            evidenceCount=handle.accumulator.evidenceCount,
            telemetry=telemetry,
            status=METRIC_STATUS[status],
        )
