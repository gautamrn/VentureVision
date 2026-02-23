from pydantic import BaseModel, HttpUrl


class EvidenceItem(BaseModel):
    query: str
    title: str
    snippet: str
    source_url: HttpUrl


class MarketCompetitor(BaseModel):
    competitor: str
    pricing: str
    funding: str


class Subscores(BaseModel):
    market_size: int
    competition: int
    revenue_model: int
    uniqueness: int


class InvestorQuestion(BaseModel):
    question: str
    why_it_matters: str


class PitchAnnotation(BaseModel):
    excerpt: str
    annotation_type: str
    note: str


class DealContext(BaseModel):
    typical_stage: str
    typical_raise_range: str
    typical_dilution: str
    red_flags: list[str]


class MemoOutput(BaseModel):
    pitch_score: int
    subscores: Subscores
    strengthen_suggestions: list[str]
    executive_summary: str
    market_matrix: list[MarketCompetitor]
    risk_vectors: list[str]
    confidence_score: float
    citation_links: list[HttpUrl]
    investor_questions: list[InvestorQuestion]
    pitch_annotations: list[PitchAnnotation]
    deal_context: DealContext
    feature_suggestions: list[str]


class PitchRequest(BaseModel):
    pitch: str
    mode: str = "quick_check"


class RunResponse(BaseModel):
    status: str
    iterations: int
    memo: MemoOutput
