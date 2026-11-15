import operator
from typing import Annotated, TypedDict

from app.schemas.models import EvidenceItem, LlmCall, MemoOutput, NodeTiming, SearchCall


class AgentState(TypedDict):
    pitch: str
    mode: str
    research_plan: list[str]
    raw_evidence: list[EvidenceItem]
    analysis_iteration: int
    is_validated: bool
    critique_feedback: str
    coverage_score: float
    final_memo: MemoOutput | None
    budget_usd: float
    budget_exit_reason: str | None
    llm_calls: Annotated[list[LlmCall], operator.add]
    search_calls: Annotated[list[SearchCall], operator.add]
    node_timings: Annotated[list[NodeTiming], operator.add]
