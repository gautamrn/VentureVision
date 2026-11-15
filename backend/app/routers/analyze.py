import asyncio
import json
import os
import threading
import time
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.schemas.models import PitchRequest, RunResponse
from app.graph.workflow import ventureGraph
from app.middleware.rateLimiter import rateLimitGuard
from app.middleware.metrics import recordRun, getMetrics
from app.telemetry.budget import configuredBudgetUsd
from app.telemetry.summary import RunAccumulator, summarizeRun

router = APIRouter()

ADMIN_KEY = os.getenv("ADMIN_KEY", "")
MAX_CONCURRENT_STREAMS = 5
_streamSemaphore = asyncio.Semaphore(MAX_CONCURRENT_STREAMS)


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


def elapsedMs(startPerf: float) -> int:
    return round((time.perf_counter() - startPerf) * 1000)


def serializeNodeOutput(nodeName: str, nodeState: dict) -> dict:
    if nodeName == "planner":
        queries = nodeState.get("research_plan", [])
        return {"queries": queries, "queryCount": len(queries)}

    if nodeName == "scout":
        evidence = nodeState.get("raw_evidence", [])
        searches = nodeState.get("search_calls", [])
        return {
            "evidenceCount": len(evidence),
            "searches": len(searches),
            "failedSearches": sum(1 for s in searches if s.error),
        }

    if nodeName == "critic":
        return {
            "iteration": nodeState.get("analysis_iteration", 1),
            "isValidated": nodeState.get("is_validated", False),
            "coverageScore": nodeState.get("coverage_score", 0.0),
            "feedback": nodeState.get("critique_feedback", ""),
            "budgetExitReason": nodeState.get("budget_exit_reason"),
        }

    if nodeName == "writer":
        return {"memoReady": nodeState.get("final_memo") is not None}

    if nodeName == "citation_audit":
        memo = nodeState.get("final_memo")
        if memo is not None and hasattr(memo, "model_dump"):
            return {"memo": memo.model_dump(mode="json")}
        return {"memo": None}

    return {}


@router.get("/admin/metrics", dependencies=[Depends(verifyAdminKey)])
async def adminMetrics():
    return getMetrics()


@router.post("/analyze", response_model=RunResponse, dependencies=[Depends(rateLimitGuard)])
async def analyze(request: PitchRequest):
    startTime = time.time()
    startPerf = time.perf_counter()
    initialState = buildInitialState(request.pitch, request.mode)
    result = await asyncio.to_thread(ventureGraph.invoke, initialState)

    telemetry = summarizeRun(
        llmCalls=result["llm_calls"],
        searchCalls=result["search_calls"],
        nodeTimings=result["node_timings"],
        durationMs=elapsedMs(startPerf),
        budgetUsd=initialState["budget_usd"],
        budgetExitReason=result.get("budget_exit_reason"),
    )
    memo = result["final_memo"]
    recordRun(
        runId=uuid.uuid4().hex,
        startTime=startTime,
        mode=request.mode,
        pitchScore=memo.pitch_score if memo else None,
        iterations=result["analysis_iteration"],
        evidenceCount=len(result.get("raw_evidence", [])),
        telemetry=telemetry,
        status="success" if memo else "error",
    )

    if memo is None:
        raise HTTPException(status_code=502, detail="Analysis failed. Please try again.")
    memo = memo.model_copy(update={"telemetry": telemetry})

    return RunResponse(
        status="complete",
        iterations=result["analysis_iteration"],
        memo=memo,
    )


@router.post("/analyze/stream", dependencies=[Depends(rateLimitGuard)])
async def analyzeStream(request: PitchRequest):
    if _streamSemaphore.locked():
        raise HTTPException(status_code=503, detail="Server busy. Try again in a minute.")

    initialState = buildInitialState(request.pitch, request.mode)
    startTime = time.time()
    startPerf = time.perf_counter()

    async def eventGenerator():
        async with _streamSemaphore:
            queue: asyncio.Queue = asyncio.Queue()
            loop = asyncio.get_event_loop()
            accumulator = RunAccumulator()
            status = "success"

            def runGraph():
                try:
                    for chunk in ventureGraph.stream(initialState):
                        nodeName = list(chunk.keys())[0]
                        nodeState = chunk[nodeName]
                        loop.call_soon_threadsafe(
                            queue.put_nowait, (nodeName, nodeState, None)
                        )
                except Exception as e:
                    loop.call_soon_threadsafe(queue.put_nowait, (None, None, str(e)))
                finally:
                    loop.call_soon_threadsafe(queue.put_nowait, None)

            thread = threading.Thread(target=runGraph, daemon=True)
            thread.start()

            while True:
                item = await queue.get()
                if item is None:
                    break

                nodeName, nodeState, error = item

                if error:
                    status = "error"
                    yield {"event": "error", "data": json.dumps({"message": error})}
                    break

                accumulator.apply(nodeState)
                if nodeName == "citation_audit" and nodeState.get("final_memo") is not None:
                    telemetry = accumulator.summarize(elapsedMs(startPerf), initialState["budget_usd"])
                    nodeState = {
                        **nodeState,
                        "final_memo": nodeState["final_memo"].model_copy(update={"telemetry": telemetry}),
                    }

                payload = serializeNodeOutput(nodeName, nodeState)
                yield {"event": nodeName, "data": json.dumps(payload)}

            recordRun(
                runId=uuid.uuid4().hex,
                startTime=startTime,
                mode=request.mode,
                pitchScore=accumulator.pitchScore,
                iterations=accumulator.iterations,
                evidenceCount=accumulator.evidenceCount,
                telemetry=accumulator.summarize(elapsedMs(startPerf), initialState["budget_usd"]),
                status=status,
            )

    return EventSourceResponse(eventGenerator())
