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


class MemoOutput(BaseModel):
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
