# Data Schemas

## Agent State (Python)
class AgentState(TypedDict):
    pitch: str
    research_plan: List[str]
    raw_evidence: List[Dict]
    analysis_iteration: int
    is_validated: bool
    final_memo: str

## Memo Object (JSON/Zod)
- executive_summary: string
- market_matrix: Array<{competitor: string, pricing: string, funding: string}>
- risk_vectors: Array<string>
- citation_links: Array<string (URL)>