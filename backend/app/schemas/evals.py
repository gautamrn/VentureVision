from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

EvalLabel = Literal["supported", "unsupported", "contradicted"]
EvalMode = Literal["heuristic", "llm"]
CaseOrigin = Literal["seed-real", "seed-constructed", "feedback"]

EVAL_LABELS: tuple[EvalLabel, ...] = ("supported", "unsupported", "contradicted")

# Memo verdicts collapse onto the eval labels: only "strong" asserts support, and every
# no-evidence or partial verdict ("needs_research", "weak_claim", ...) asserts none.
LABEL_FOR_VERDICT: dict[str, EvalLabel] = {
    "strong": "supported",
    "contradicted": "contradicted",
    "needs_research": "unsupported",
    "weak_claim": "unsupported",
    "vague": "unsupported",
    "unsubstantiated": "unsupported",
}


class EvidenceSnippet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_url: str | None
    title: str
    text: str


class GoldenCase(BaseModel):
    """One line of evals/golden_dataset.jsonl (and of evals/candidates.jsonl)."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    pitch_excerpt: str
    claim: str = Field(min_length=1)
    evidence: list[EvidenceSnippet]
    label: EvalLabel
    origin: CaseOrigin
    notes: str


class DatasetManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    version: int = Field(ge=1)
    updated: str
    changelog: list[str]


class Prediction(BaseModel):
    label: EvalLabel
    detail: str
    downgraded_from: EvalLabel | None = None


class CaseOutcome(BaseModel):
    id: str
    expected: EvalLabel
    predicted: EvalLabel
    correct: bool
    detail: str
    downgraded_from: EvalLabel | None = None


class LabelScore(BaseModel):
    label: EvalLabel
    total: int
    correct: int
    accuracy: float


class EvalRun(BaseModel):
    run_id: str
    mode: EvalMode
    model: str | None
    dataset_version: int
    dataset_sha256: str
    case_count: int
    started_at: datetime
    duration_ms: int
    cost_usd: float
    overall_accuracy: float
    labels: list[LabelScore]
    cases: list[CaseOutcome]


class EvalBaseline(BaseModel):
    run_id: str
    mode: EvalMode
    dataset_version: int
    case_count: int
    overall_accuracy: float
    labels: list[LabelScore]


class RunSummary(BaseModel):
    run_id: str
    mode: EvalMode
    model: str | None
    started_at: datetime
    dataset_version: int
    case_count: int
    overall_accuracy: float
    labels: list[LabelScore]
    cost_usd: float


class FailedCase(BaseModel):
    id: str
    origin: CaseOrigin
    claim: str
    pitch_excerpt: str
    evidence: list[EvidenceSnippet]
    expected: EvalLabel
    predicted: EvalLabel
    detail: str
    downgraded_from: EvalLabel | None
    notes: str


class LatestRun(RunSummary):
    failures: list[FailedCase]


class DatasetSummary(BaseModel):
    name: str
    version: int
    updated: str
    case_count: int
    label_counts: dict[EvalLabel, int]
    origin_counts: dict[CaseOrigin, int]
    candidate_count: int


class EvalSummary(BaseModel):
    """Everything the /evals page and the MCP get_eval_scores tool show, built from stored runs only."""

    generated_at: datetime
    dataset: DatasetSummary
    baseline: EvalBaseline | None
    latest_heuristic: LatestRun | None
    latest_llm: LatestRun | None
    history: list[RunSummary]
