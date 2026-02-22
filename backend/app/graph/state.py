from typing import TypedDict

from app.schemas.models import EvidenceItem, MemoOutput


class AgentState(TypedDict):
    pitch: str
    research_plan: list[str]
    raw_evidence: list[EvidenceItem]
    analysis_iteration: int
    is_validated: bool
    critique_feedback: str
    coverage_score: float
    final_memo: MemoOutput | None
