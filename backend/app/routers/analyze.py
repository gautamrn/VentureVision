import asyncio
import json
import threading

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from app.schemas.models import PitchRequest, RunResponse
from app.graph.workflow import ventureGraph
from app.middleware.rateLimiter import rateLimitGuard

router = APIRouter()


def buildInitialState(pitch: str, mode: str = "quick_check") -> dict:
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
    }


def serializeNodeOutput(nodeName: str, nodeState: dict) -> dict:
    if nodeName == "planner":
        queries = nodeState.get("research_plan", [])
        return {"queries": queries, "queryCount": len(queries)}

    if nodeName == "scout":
        evidence = nodeState.get("raw_evidence", [])
        return {"evidenceCount": len(evidence)}

    if nodeName == "critic":
        return {
            "iteration": nodeState.get("analysis_iteration", 1),
            "isValidated": nodeState.get("is_validated", False),
            "coverageScore": nodeState.get("coverage_score", 0.0),
            "feedback": nodeState.get("critique_feedback", ""),
        }

    if nodeName == "writer":
        memo = nodeState.get("final_memo")
        if memo is not None and hasattr(memo, "model_dump"):
            return {"memo": memo.model_dump(mode="json")}
        return {"memo": None}

    return {}


@router.post("/analyze", response_model=RunResponse, dependencies=[Depends(rateLimitGuard)])
async def analyze(request: PitchRequest):
    result = await asyncio.to_thread(
        ventureGraph.invoke, buildInitialState(request.pitch, request.mode)
    )

    return RunResponse(
        status="complete",
        iterations=result["analysis_iteration"],
        memo=result["final_memo"],
    )


@router.post("/analyze/stream", dependencies=[Depends(rateLimitGuard)])
async def analyzeStream(request: PitchRequest):
    initialState = buildInitialState(request.pitch, request.mode)

    async def eventGenerator():
        queue: asyncio.Queue = asyncio.Queue()
        loop = asyncio.get_event_loop()

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
                yield {"event": "error", "data": json.dumps({"message": error})}
                break

            payload = serializeNodeOutput(nodeName, nodeState)
            yield {"event": nodeName, "data": json.dumps(payload)}

    return EventSourceResponse(eventGenerator())
