from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.evals import EvalLabel
from app.schemas.models import AnalysisMode, AnnotationType, MemoOutput, ShareSeal

UserVerdict = Literal["correct", "wrong"]
ReviewStatus = Literal["pending", "accepted", "rejected"]
FeedbackOrigin = Literal["live", "demo"]
FeedbackView = Literal["disagreements", "all"]


class FeedbackRequest(BaseModel):
    """A reader's correct / wrong on one claim verdict, sent with the memo it belongs to."""

    model_config = ConfigDict(extra="forbid")

    pitch: str = Field(..., min_length=1, max_length=5000)
    mode: AnalysisMode
    memo: MemoOutput
    seal: ShareSeal | None = None
    demo_sample_id: str | None = Field(default=None, pattern=r"^[a-z0-9-]{1,40}$")
    annotation_index: int = Field(..., ge=0)
    user_verdict: UserVerdict

    @model_validator(mode="after")
    def annotationExists(self) -> "FeedbackRequest":
        if self.annotation_index >= len(self.memo.pitch_annotations):
            raise ValueError(f"annotation_index {self.annotation_index} is out of range for this memo")
        return self


class FeedbackCreated(BaseModel):
    feedback_id: int
    verified: bool


class FeedbackRecord(BaseModel):
    feedback_id: int
    created_at: datetime
    origin: FeedbackOrigin
    verified: bool
    mode: AnalysisMode
    pitch_excerpt: str
    claim: str
    evidence_quote: str | None
    evidence_url: str | None
    model_verdict: AnnotationType
    downgraded_from: AnnotationType | None
    user_verdict: UserVerdict
    status: ReviewStatus
    gold_label: EvalLabel | None
    reviewer_note: str
    reviewed_at: datetime | None
    exported_at: datetime | None


class FeedbackCounts(BaseModel):
    total: int
    disagreements: int
    pending: int
    accepted: int
    rejected: int
    exported: int


class FeedbackList(BaseModel):
    counts: FeedbackCounts
    records: list[FeedbackRecord]


class FeedbackReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["accepted", "rejected"]
    gold_label: EvalLabel | None = None
    note: str = Field(default="", max_length=1000)

    @model_validator(mode="after")
    def acceptedNeedsLabel(self) -> "FeedbackReview":
        if self.status == "accepted" and self.gold_label is None:
            raise ValueError("accepting feedback requires the correct gold_label")
        return self
