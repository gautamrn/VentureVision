import asyncio
import json
import os
import threading
import time
import uuid
from typing import Callable, Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.graph.errors import NodeFailure
from app.graph.workflow import ventureGraph
from app.middleware.metrics import getMetrics, recordRun
from app.middleware.rateLimiter import rateLimitGuard
from app.runs.events import serializeNodeOutput
from app.runs.executor import executeAttempt, registry
from app.runs.registry import RunBusyError, RunHandle, RunStateError
from app.schemas.models import MemoOutput, PitchRequest, RunResponse
from app.telemetry.budget import configuredBudgetUsd
from app.telemetry.summary import RunAccumulator

__all__ = ["router", "buildInitialState", "runToCompletion", "serializeNodeOutput"]

router = APIRouter()

ADMIN_KEY = os.getenv("ADMIN_KEY", "")


class CancelResponse(BaseModel):
    runId: str
    status: Literal["cancelling"]


async def verifyAdminKey(x_admin_key: str = Header(None)) -> None:
    if not ADMIN_KEY or x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized")


def buildInitialState(pitch: str, mode: str = "market_scan", budgetUsd: float | None = None) -> dict:
    return {
        "pitch": pitch,
        "mode": mode,
        "research_plan": [],
        "raw_evidence": [],
        "analysis_iteration": 0,
        "is_validated": False,
        "critique_feedback": "",
        "coverage_score": 0.0,
        "final_memo": None,
        "budget_usd": configuredBudgetUsd() if budgetUsd is None else budgetUsd,
        "budget_exit_reason": None,
        "llm_calls": [],
        "search_calls": [],
        "node_timings": [],
    }


def runToCompletion(
    initialState: dict, onNode: Callable[[str], None] = lambda _: None
) -> tuple[RunAccumulator, MemoOutput | None, NodeFailure | None]:
    accumulator = RunAccumulator()
    finalMemo = None
    try:
        for chunk in ventureGraph.stream(initialState, stream_mode="updates"):
            for nodeName, update in chunk.items():
                accumulator.apply(update)
                onNode(nodeName)
                if nodeName == "citation_audit":
                    finalMemo = update.get("final_memo")
    except NodeFailure as exc:
        accumulator.addPartial(exc.node, exc.llmCalls, exc.searchCalls, exc.durationMs)
        return accumulator, None, exc
    return accumulator, finalMemo, None


def streamAttempt(handle: RunHandle, graphInput: dict | None) -> EventSourceResponse:
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def emit(name: str | None, payload: dict | None) -> None:
        try:
            loop.call_soon_threadsafe(queue.put_nowait, (name, payload))
        except RuntimeError:
            pass  # event loop already closed: nobody is listening any more

    def work() -> None:
        try:
            executeAttempt(handle, graphInput, emit)
        finally:
            emit(None, None)

    async def events():
        finished = False
        try:
            yield {
                "event": "run",
                "data": json.dumps(
                    {
                        "runId": handle.runId,
                        "attempt": handle.attempt,
                        "retriesLeft": handle.retriesLeft,
                        "budgetUsd": handle.budgetUsd,
                    }
                ),
            }
            while True:
                name, payload = await queue.get()
                if name is None:
                    finished = True
                    return
                yield {"event": name, "data": json.dumps(payload)}
        finally:
            if not finished:
                # The client went away mid-run: stop the graph before its next step.
                handle.control.cancel()

    threading.Thread(target=work, name=f"run-{handle.runId[:8]}", daemon=True).start()
    return EventSourceResponse(events())


@router.get("/admin/metrics", dependencies=[Depends(verifyAdminKey)])
async def adminMetrics():
    return getMetrics()


@router.post("/analyze", response_model=RunResponse, dependencies=[Depends(rateLimitGuard)])
async def analyze(request: PitchRequest):
    startTime = time.time()
    startPerf = time.perf_counter()
    initialState = buildInitialState(request.pitch, request.mode)
    accumulator, memo, failure = await asyncio.to_thread(runToCompletion, initialState)

    telemetry = accumulator.summarize(round((time.perf_counter() - startPerf) * 1000), initialState["budget_usd"])
    recordRun(
        runId=uuid.uuid4().hex,
        startTime=startTime,
        mode=request.mode,
        pitchScore=accumulator.pitchScore,
        iterations=accumulator.iterations,
        evidenceCount=accumulator.evidenceCount,
        telemetry=telemetry,
        status="success" if memo else "error",
    )

    if failure is not None:
        raise HTTPException(status_code=502, detail=failure.message)
    if memo is None:
        raise HTTPException(status_code=502, detail="Analysis finished without a memo.")

    return RunResponse(
        status="complete",
        iterations=accumulator.iterations,
        memo=memo.model_copy(update={"telemetry": telemetry}),
    )


@router.post("/analyze/stream", dependencies=[Depends(rateLimitGuard)])
async def analyzeStream(request: PitchRequest):
    try:
        handle = registry.start(request.mode, configuredBudgetUsd(), request.pitch)
    except RunBusyError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return streamAttempt(handle, buildInitialState(request.pitch, request.mode, handle.budgetUsd))


@router.post("/runs/{runId}/retry")
async def retryRun(runId: str):
    try:
        handle = registry.resume(runId)
    except KeyError:
        raise HTTPException(status_code=404, detail="Run not found or its retry window has expired.")
    except RunStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except RunBusyError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return streamAttempt(handle, None)


@router.post("/runs/{runId}/cancel", response_model=CancelResponse)
async def cancelRun(runId: str):
    handle = registry.get(runId)
    if handle is None:
        raise HTTPException(status_code=404, detail="Run not found.")
    if handle.status != "running":
        raise HTTPException(status_code=409, detail=f"Run already {handle.status}.")
    handle.control.cancel()
    return CancelResponse(runId=runId, status="cancelling")
