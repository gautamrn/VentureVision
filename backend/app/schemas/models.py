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


class MemoOutput(BaseModel):
    pitch_score: int
    subscores: Subscores
    strengthen_suggestions: list[str]
    executive_summary: str
    market_matrix: list[MarketCompetitor]
    risk_vectors: list[str]
    confidence_score: float
    citation_links: list[HttpUrl]


class PitchRequest(BaseModel):
    pitch: str


class RunResponse(BaseModel):
    status: str
    iterations: int
    memo: MemoOutput
