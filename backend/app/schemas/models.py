from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator

AnnotationType = Literal[
    "strong",
    "contradicted",
    "needs_research",
    "weak_claim",
    "vague",
    "unsubstantiated",
]


class EvidenceItem(BaseModel):
    query: str
    title: str
    snippet: str
    source_url: HttpUrl
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Citation(BaseModel):
    quote: str
    source_url: HttpUrl
    retrieved_at: datetime


class MarketCompetitor(BaseModel):
    competitor: str
    pricing: str
    funding: str
    citation: Citation | None = None


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
    annotation_type: AnnotationType
    note: str
    citation: Citation | None = None
    downgraded_from: AnnotationType | None = None


class Groundedness(BaseModel):
    cited_claims: int
    total_claims: int
    downgraded_claims: int


class DealContext(BaseModel):
    typical_stage: str
    typical_raise_range: str
    typical_dilution: str
    red_flags: list[str]


class LlmCall(BaseModel):
    node: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float


class SearchCall(BaseModel):
    node: str
    query: str
    result_count: int
    credits: int
    cost_usd: float
    error: str | None = None


class NodeTiming(BaseModel):
    node: str
    duration_ms: int


class NodeLatency(BaseModel):
    node: str
    runs: int
    total_ms: int


class RunTelemetry(BaseModel):
    agent_count: int
    duration_ms: int
    llm_calls: int
    prompt_tokens: int
    completion_tokens: int
    search_calls: int
    failed_searches: int
    llm_cost_usd: float
    search_cost_usd: float
    total_cost_usd: float
    budget_usd: float
    budget_exit_reason: str | None = None
    nodes: list[NodeLatency]
    pricing_as_of: str


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
    groundedness: Groundedness | None = None
    telemetry: RunTelemetry | None = None


AnalysisMode = Literal["market_scan", "pitch_lab"]
ShareKind = Literal["memo", "compare"]


class PitchRequest(BaseModel):
    pitch: str = Field(..., min_length=40, max_length=5000)
    mode: AnalysisMode = "market_scan"


class ShareSeal(BaseModel):
    """Server signature over (pitch, mode, generated_at, memo): proof this server produced the memo."""

    generated_at: datetime
    signature: str = Field(..., min_length=64, max_length=64)


class SealedMemo(BaseModel):
    pitch: str = Field(..., min_length=1, max_length=5000)
    mode: AnalysisMode
    memo: MemoOutput
    seal: ShareSeal


class ShareRequest(BaseModel):
    kind: ShareKind
    memos: list[SealedMemo] = Field(..., min_length=1, max_length=2)

    @model_validator(mode="after")
    def memoCountMatchesKind(self) -> "ShareRequest":
        expected = 1 if self.kind == "memo" else 2
        if len(self.memos) != expected:
            raise ValueError(f"a {self.kind} share needs exactly {expected} memo(s)")
        return self


class SharedMemo(BaseModel):
    pitch: str
    mode: AnalysisMode
    generated_at: datetime
    memo: MemoOutput


class ShareCreated(BaseModel):
    share_id: str
    created_at: datetime


class ShareView(BaseModel):
    share_id: str
    kind: ShareKind
    created_at: datetime
    memos: list[SharedMemo]


class RunResponse(BaseModel):
    status: str
    iterations: int
    memo: MemoOutput | None
