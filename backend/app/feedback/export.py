import json
from dataclasses import dataclass, field
from pathlib import Path

from app.evals.dataset import loadCases
from app.feedback.store import FeedbackStore
from app.schemas.evals import EvidenceSnippet, GoldenCase
from app.schemas.feedback import FeedbackRecord


@dataclass
class ExportReport:
    appended: list[str] = field(default_factory=list)
    skipped: list[tuple[int, str]] = field(default_factory=list)


def candidateId(record: FeedbackRecord) -> str:
    return f"fb-{record.feedback_id}"


def candidateFrom(record: FeedbackRecord) -> GoldenCase:
    if record.gold_label is None:
        raise ValueError(f"feedback {record.feedback_id} has no reviewed gold_label")
    evidence = (
        [EvidenceSnippet(source_url=record.evidence_url, title="", text=record.evidence_quote)]
        if record.evidence_quote
        else []
    )
    downgrade = f" (downgraded from {record.downgraded_from})" if record.downgraded_from else ""
    provenance = "a sealed live run" if record.verified else f"an unverified {record.origin} memo"
    reviewerNote = record.reviewer_note.strip().rstrip(".") or "no note"
    return GoldenCase(
        id=candidateId(record),
        pitch_excerpt=record.pitch_excerpt,
        claim=record.claim,
        evidence=evidence,
        label=record.gold_label,
        origin="feedback",
        notes=(
            f"Feedback #{record.feedback_id} from {provenance}: the model said {record.model_verdict}{downgrade}, "
            f"the reader said {record.user_verdict}. Reviewer: {reviewerNote}."
        ),
    )


def exportAccepted(store: FeedbackStore, candidatesPath: Path, goldenPath: Path) -> ExportReport:
    """Appends reviewed feedback to the candidates file. Never writes the golden dataset; a human promotes cases."""
    report = ExportReport()
    taken = {c.id for c in loadCases(goldenPath)} | {c.id for c in loadCases(candidatesPath)}
    lines: list[str] = []
    exported: list[int] = []
    for record in store.acceptedUnexported():
        if candidateId(record) in taken:
            report.skipped.append((record.feedback_id, "already in the candidates or golden file"))
            continue
        if record.gold_label != "unsupported" and not record.evidence_quote:
            report.skipped.append((record.feedback_id, f"a {record.gold_label} label needs an evidence quote; reject it instead"))
            continue
        case = candidateFrom(record)
        lines.append(json.dumps(case.model_dump(mode="json"), ensure_ascii=False))
        report.appended.append(case.id)
        exported.append(record.feedback_id)

    if lines:
        candidatesPath.parent.mkdir(parents=True, exist_ok=True)
        existing = candidatesPath.read_text(encoding="utf-8") if candidatesPath.exists() else ""
        separator = "" if not existing or existing.endswith("\n") else "\n"
        with candidatesPath.open("a", encoding="utf-8") as handle:
            handle.write(separator + "\n".join(lines) + "\n")
        store.markExported(exported)
    return report
