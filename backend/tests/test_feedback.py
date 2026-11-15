import json
from pathlib import Path

import pytest

from app.evals.dataset import datasetPath, loadCases
from app.feedback.export import exportAccepted
from app.feedback.store import FeedbackStore, getFeedbackStore, pitchExcerptAround
from app.main import app
from app.schemas.evals import GoldenCase
from app.schemas.feedback import FeedbackReview
from app.schemas.models import MemoOutput
from app.shares.sealing import sealMemo

ADMIN = {"X-Admin-Key": "test-admin-key"}
PITCH = (
    "Tablebook is a booking tool for independent restaurants. "
    "Restaurants lose 20% of covers to no-shows every month. "
    "We charge $99 per location."
)
STRONG_CLAIM = "Restaurants lose 20% of covers to no-shows"
STRONG_QUOTE = "no-shows cost restaurants up to 20% of covers"
SOURCE = "https://example.com/no-show-report"


def memoDict() -> dict:
    return {
        "pitch_score": 70,
        "subscores": {"market_size": 70, "competition": 60, "revenue_model": 70, "uniqueness": 50},
        "strengthen_suggestions": [],
        "executive_summary": "Summary.",
        "market_matrix": [],
        "risk_vectors": [],
        "confidence_score": 0.8,
        "citation_links": [SOURCE],
        "investor_questions": [],
        "pitch_annotations": [
            {
                "excerpt": STRONG_CLAIM,
                "annotation_type": "strong",
                "note": "Backed by an industry report.",
                "citation": {"quote": STRONG_QUOTE, "source_url": SOURCE, "retrieved_at": "2026-11-15T12:00:00Z"},
            },
            {
                "excerpt": "We charge $99 per location",
                "annotation_type": "needs_research",
                "note": "No pricing benchmark found.",
                "downgraded_from": "strong",
            },
        ],
        "deal_context": {"typical_stage": "Seed", "typical_raise_range": "$1-3M", "typical_dilution": "15-20%", "red_flags": []},
        "feature_suggestions": [],
    }


def sealedPayload(annotationIndex: int = 0, userVerdict: str = "wrong") -> dict:
    memo = MemoOutput.model_validate(memoDict())
    seal = sealMemo(PITCH, "market_scan", memo)
    return {
        "pitch": PITCH,
        "mode": "market_scan",
        "memo": memo.model_dump(mode="json"),
        "seal": seal.model_dump(mode="json"),
        "annotation_index": annotationIndex,
        "user_verdict": userVerdict,
    }


@pytest.fixture
def feedbackStore(tmp_path):
    store = FeedbackStore(tmp_path / "feedback.sqlite3")
    app.dependency_overrides[getFeedbackStore] = lambda: store
    yield store
    app.dependency_overrides.pop(getFeedbackStore, None)


def testFeedbackStoresClaimEvidenceAndBothVerdictsButNotTheWholePitch(client, feedbackStore):
    response = client.post("/feedback", json=sealedPayload())

    assert response.status_code == 201
    assert response.json()["verified"] is True
    record = feedbackStore.get(response.json()["feedback_id"])
    assert record.claim == STRONG_CLAIM
    assert record.pitch_excerpt == "Restaurants lose 20% of covers to no-shows every month."
    assert (record.evidence_quote, record.evidence_url) == (STRONG_QUOTE, SOURCE)
    assert (record.model_verdict, record.user_verdict, record.status) == ("strong", "wrong", "pending")
    assert (record.origin, record.gold_label, record.exported_at) == ("live", None, None)


def testDemoFeedbackIsKeptButMarkedUnverified(client, feedbackStore):
    payload = sealedPayload(annotationIndex=1, userVerdict="correct")
    payload.pop("seal")
    payload["demo_sample_id"] = "tablebook"

    response = client.post("/feedback", json=payload)

    assert response.status_code == 201
    record = feedbackStore.get(response.json()["feedback_id"])
    assert (record.origin, record.verified, record.downgraded_from) == ("demo", False, "strong")
    assert record.evidence_quote is None


def testFeedbackOnATamperedMemoIsRejected(client, feedbackStore):
    payload = sealedPayload()
    payload["memo"]["pitch_annotations"][0]["annotation_type"] = "contradicted"

    response = client.post("/feedback", json=payload)

    assert response.status_code == 403
    assert feedbackStore.listRecords("all").counts.total == 0


@pytest.mark.parametrize(
    "change",
    [
        {"annotation_index": 2},
        {"annotation_index": -1},
        {"user_verdict": "maybe"},
        {"pitch_text": "unexpected field"},
    ],
)
def testInvalidFeedbackIsRejected(client, feedbackStore, change):
    response = client.post("/feedback", json={**sealedPayload(), **change})

    assert response.status_code == 422
    assert feedbackStore.listRecords("all").counts.total == 0


def testFeedbackIsRateLimited(client, feedbackStore):
    for _ in range(60):
        assert client.post("/feedback", json=sealedPayload()).status_code == 201
    assert client.post("/feedback", json=sealedPayload()).status_code == 429


def testAdminFeedbackRequiresTheAdminKey(client, feedbackStore):
    assert client.get("/admin/feedback").status_code == 403
    assert client.get("/admin/feedback", headers={"X-Admin-Key": "wrong"}).status_code == 403
    assert client.post("/admin/feedback/1/review", json={"status": "rejected"}).status_code == 403


def testDisagreementsListStrongButWrongFirst(client, feedbackStore):
    client.post("/feedback", json=sealedPayload(annotationIndex=1, userVerdict="wrong"))
    client.post("/feedback", json=sealedPayload(annotationIndex=0, userVerdict="correct"))
    client.post("/feedback", json=sealedPayload(annotationIndex=0, userVerdict="wrong"))

    body = client.get("/admin/feedback", headers=ADMIN).json()

    assert body["counts"] == {"total": 3, "disagreements": 2, "pending": 3, "accepted": 0, "rejected": 0, "exported": 0}
    assert [(r["model_verdict"], r["user_verdict"]) for r in body["records"]] == [("strong", "wrong"), ("needs_research", "wrong")]
    everything = client.get("/admin/feedback", params={"view": "all"}, headers=ADMIN).json()
    assert len(everything["records"]) == 3


def testAcceptingFeedbackRequiresTheCorrectLabel(client, feedbackStore):
    feedbackId = client.post("/feedback", json=sealedPayload()).json()["feedback_id"]

    missing = client.post(f"/admin/feedback/{feedbackId}/review", json={"status": "accepted"}, headers=ADMIN)
    accepted = client.post(
        f"/admin/feedback/{feedbackId}/review",
        json={"status": "accepted", "gold_label": "unsupported", "note": "Report says 'up to', not every month."},
        headers=ADMIN,
    )
    unknown = client.post("/admin/feedback/999/review", json={"status": "rejected"}, headers=ADMIN)

    assert missing.status_code == 422
    assert accepted.status_code == 200
    assert (accepted.json()["status"], accepted.json()["gold_label"]) == ("accepted", "unsupported")
    assert unknown.status_code == 404


def testPitchExcerptIsTheSentenceAroundTheClaim():
    assert pitchExcerptAround(PITCH, "we charge $99") == "We charge $99 per location."
    assert pitchExcerptAround(PITCH, "not in the pitch") == ""


def addReviewed(store: FeedbackStore, annotationIndex: int, goldLabel: str | None, status: str = "accepted") -> int:
    memo = MemoOutput.model_validate(memoDict())
    record = store.add(
        pitch=PITCH,
        mode="market_scan",
        annotation=memo.pitch_annotations[annotationIndex],
        userVerdict="wrong",
        origin="live",
        verified=True,
    )
    store.review(record.feedback_id, FeedbackReview(status=status, gold_label=goldLabel, note="checked the source"))
    return record.feedback_id


def goldenLines() -> list[dict]:
    return [json.loads(line) for line in datasetPath().read_text(encoding="utf-8").splitlines() if line.strip()]


def testExportedCandidatesMatchTheGoldenDatasetSchemaExactly(tmp_path):
    store = FeedbackStore(tmp_path / "feedback.sqlite3")
    addReviewed(store, 0, "unsupported")
    addReviewed(store, 1, "unsupported")
    candidates = tmp_path / "candidates.jsonl"

    report = exportAccepted(store, candidates, datasetPath())

    golden = goldenLines()
    exported = [json.loads(line) for line in candidates.read_text(encoding="utf-8").splitlines()]
    assert report.appended == ["fb-1", "fb-2"]
    assert len(exported) == 2
    goldenKeys = {tuple(case) for case in golden}
    goldenEvidenceKeys = {tuple(item) for case in golden for item in case["evidence"]}
    assert len(goldenKeys) == 1 and len(goldenEvidenceKeys) == 1
    for case in exported:
        assert tuple(case) in goldenKeys, "same keys in the same order as golden_dataset.jsonl"
        assert all(tuple(item) in goldenEvidenceKeys for item in case["evidence"])
        assert {k: type(v) for k, v in case.items() if k != "evidence"} == {
            k: type(v) for k, v in golden[0].items() if k != "evidence"
        }
        assert GoldenCase.model_validate(case).origin == "feedback"
    assert exported[0]["evidence"] == [{"source_url": SOURCE, "title": "", "text": STRONG_QUOTE}]
    assert exported[0]["pitch_excerpt"] == "Restaurants lose 20% of covers to no-shows every month."
    assert exported[1]["evidence"] == []
    assert [c.id for c in loadCases(candidates)] == ["fb-1", "fb-2"]


def testExportAppendsOnlyAcceptedRowsOnceAndNeverTouchesTheGoldenSet(tmp_path):
    store = FeedbackStore(tmp_path / "feedback.sqlite3")
    goldenCopy = tmp_path / "golden_dataset.jsonl"
    goldenCopy.write_bytes(datasetPath().read_bytes())
    goldenBefore = goldenCopy.read_bytes()
    candidates = tmp_path / "candidates.jsonl"
    candidates.write_text("", encoding="utf-8")

    accepted = addReviewed(store, 0, "supported")
    addReviewed(store, 0, None, status="rejected")
    store.add(
        pitch=PITCH,
        mode="market_scan",
        annotation=MemoOutput.model_validate(memoDict()).pitch_annotations[0],
        userVerdict="wrong",
        origin="live",
        verified=True,
    )
    noEvidence = addReviewed(store, 1, "contradicted")

    first = exportAccepted(store, candidates, goldenCopy)
    second = exportAccepted(store, candidates, goldenCopy)

    assert first.appended == [f"fb-{accepted}"]
    assert [feedbackId for feedbackId, _ in first.skipped] == [noEvidence]
    assert second.appended == []
    assert len(candidates.read_text(encoding="utf-8").splitlines()) == 1
    assert goldenCopy.read_bytes() == goldenBefore
    assert store.get(accepted).exported_at is not None
    assert store.review(accepted, FeedbackReview(status="rejected")) is None, "exported rows are frozen"


def testCommittedCandidatesFileShipsEmpty():
    candidates = Path(datasetPath()).with_name("candidates.jsonl")
    assert candidates.exists()
    assert loadCases(candidates) == []
