import os
import re
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

from app.schemas.feedback import (
    FeedbackCounts,
    FeedbackList,
    FeedbackOrigin,
    FeedbackRecord,
    FeedbackReview,
    FeedbackView,
    UserVerdict,
)
from app.schemas.models import AnalysisMode, PitchAnnotation

DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "feedback.sqlite3"
MAX_EXCERPT_CHARS = 400
HIGH_VALUE_VERDICTS = ("strong", "contradicted")

_COLUMNS = (
    "feedback_id, created_at, origin, verified, mode, pitch_excerpt, claim, evidence_quote, evidence_url, "
    "model_verdict, downgraded_from, user_verdict, status, gold_label, reviewer_note, reviewed_at, exported_at"
)
_SENTENCE_END = re.compile(r"[.!?\n]")


def pitchExcerptAround(pitch: str, claim: str) -> str:
    """The sentence(s) of the pitch that contain the claim, so a reviewer sees context without the whole pitch."""
    start = pitch.lower().find(claim.lower())
    if start == -1:
        return ""
    end = start + len(claim)
    before = [m.end() for m in _SENTENCE_END.finditer(pitch, 0, start)]
    after = _SENTENCE_END.search(pitch, max(end - 1, start))
    sentenceStart = before[-1] if before else 0
    sentenceEnd = after.end() if after else len(pitch)
    excerpt = pitch[sentenceStart:sentenceEnd].strip()
    return excerpt if len(excerpt) <= MAX_EXCERPT_CHARS else pitch[start:end].strip()


class FeedbackStore:
    """Reader feedback on claim verdicts. Stores the claim's context, never the full pitch or who sent it."""

    def __init__(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.Lock()
        with self._lock, self._db:
            self._db.execute(
                """CREATE TABLE IF NOT EXISTS feedback (
                    feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    origin TEXT NOT NULL,
                    verified INTEGER NOT NULL,
                    mode TEXT NOT NULL,
                    pitch_excerpt TEXT NOT NULL,
                    claim TEXT NOT NULL,
                    evidence_quote TEXT,
                    evidence_url TEXT,
                    model_verdict TEXT NOT NULL,
                    downgraded_from TEXT,
                    user_verdict TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    gold_label TEXT,
                    reviewer_note TEXT NOT NULL DEFAULT '',
                    reviewed_at TEXT,
                    exported_at TEXT
                )"""
            )

    def add(
        self,
        *,
        pitch: str,
        mode: AnalysisMode,
        annotation: PitchAnnotation,
        userVerdict: UserVerdict,
        origin: FeedbackOrigin,
        verified: bool,
    ) -> FeedbackRecord:
        citation = annotation.citation
        with self._lock, self._db:
            cursor = self._db.execute(
                """INSERT INTO feedback (created_at, origin, verified, mode, pitch_excerpt, claim, evidence_quote,
                    evidence_url, model_verdict, downgraded_from, user_verdict)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    _now(),
                    origin,
                    int(verified),
                    mode,
                    pitchExcerptAround(pitch, annotation.excerpt),
                    annotation.excerpt,
                    citation.quote if citation else None,
                    str(citation.source_url) if citation else None,
                    annotation.annotation_type,
                    annotation.downgraded_from,
                    userVerdict,
                ),
            )
            return self._get(cursor.lastrowid)

    def get(self, feedbackId: int) -> FeedbackRecord | None:
        with self._lock:
            return self._get(feedbackId)

    def listRecords(self, view: FeedbackView = "disagreements") -> FeedbackList:
        where = "WHERE user_verdict = 'wrong'" if view == "disagreements" else ""
        highValue = ", ".join(f"'{v}'" for v in HIGH_VALUE_VERDICTS)
        with self._lock:
            rows = self._db.execute(
                f"""SELECT {_COLUMNS} FROM feedback {where}
                    ORDER BY (user_verdict = 'wrong' AND model_verdict IN ({highValue})) DESC,
                             status = 'pending' DESC, feedback_id DESC"""
            ).fetchall()
            counts = self._db.execute(
                """SELECT COUNT(*), SUM(user_verdict = 'wrong'), SUM(status = 'pending'), SUM(status = 'accepted'),
                          SUM(status = 'rejected'), SUM(exported_at IS NOT NULL) FROM feedback"""
            ).fetchone()
        total, disagreements, pending, accepted, rejected, exported = (value or 0 for value in counts)
        return FeedbackList(
            counts=FeedbackCounts(
                total=total, disagreements=disagreements, pending=pending, accepted=accepted, rejected=rejected, exported=exported
            ),
            records=[_record(row) for row in rows],
        )

    def review(self, feedbackId: int, review: FeedbackReview) -> FeedbackRecord | None:
        with self._lock, self._db:
            updated = self._db.execute(
                """UPDATE feedback SET status = ?, gold_label = ?, reviewer_note = ?, reviewed_at = ?
                   WHERE feedback_id = ? AND exported_at IS NULL""",
                (review.status, review.gold_label if review.status == "accepted" else None, review.note, _now(), feedbackId),
            )
            return self._get(feedbackId) if updated.rowcount else None

    def acceptedUnexported(self) -> list[FeedbackRecord]:
        with self._lock:
            rows = self._db.execute(
                f"SELECT {_COLUMNS} FROM feedback WHERE status = 'accepted' AND exported_at IS NULL ORDER BY feedback_id"
            ).fetchall()
        return [_record(row) for row in rows]

    def markExported(self, feedbackIds: list[int]) -> None:
        with self._lock, self._db:
            self._db.executemany(
                "UPDATE feedback SET exported_at = ? WHERE feedback_id = ?", [(_now(), i) for i in feedbackIds]
            )

    def _get(self, feedbackId: int) -> FeedbackRecord | None:
        row = self._db.execute(f"SELECT {_COLUMNS} FROM feedback WHERE feedback_id = ?", (feedbackId,)).fetchone()
        return _record(row) if row else None


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _record(row: tuple) -> FeedbackRecord:
    return FeedbackRecord.model_validate(dict(zip([c.strip() for c in _COLUMNS.split(",")], row)))


_store: FeedbackStore | None = None
_storeLock = threading.Lock()


def getFeedbackStore() -> FeedbackStore:
    global _store
    with _storeLock:
        if _store is None:
            _store = FeedbackStore(os.getenv("FEEDBACK_DB_PATH") or DEFAULT_DB_PATH)
        return _store
