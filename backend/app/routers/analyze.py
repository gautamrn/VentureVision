import asyncio

from fastapi import APIRouter

from app.schemas.models import PitchRequest, RunResponse
from app.graph.workflow import ventureGraph

router = APIRouter()


@router.post("/analyze", response_model=RunResponse)
async def analyze(request: PitchRequest):
    initialState = {
        "pitch": request.pitch,
        "research_plan": [],
        "raw_evidence": [],
        "analysis_iteration": 0,
        "is_validated": False,
        "critique_feedback": "",
        "final_memo": None,
    }

    result = await asyncio.to_thread(ventureGraph.invoke, initialState)

    return RunResponse(
        status="complete",
        iterations=result["analysis_iteration"],
        memo=result["final_memo"],
    )
