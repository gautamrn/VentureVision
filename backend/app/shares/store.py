import hashlib
import json
import os
import re
import secrets
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

from pydantic import TypeAdapter

from app.schemas.models import SharedMemo, ShareKind, ShareView

DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "shares.sqlite3"
SHARE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{22}$")

_memoList = TypeAdapter(list[SharedMemo])


class ShareStore:
    """Published memos. Holds only what the sharer chose to publish; nothing about who views them."""

    def __init__(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.Lock()
        with self._lock, self._db:
            self._db.execute(
                """CREATE TABLE IF NOT EXISTS shares (
                    share_id TEXT PRIMARY KEY,
                    content_hash TEXT NOT NULL UNIQUE,
                    kind TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    memos TEXT NOT NULL
                )"""
            )

    def create(self, kind: ShareKind, memos: list[SharedMemo], signatures: list[str]) -> ShareView:
        contentHash = hashlib.sha256(f"{kind}:{':'.join(signatures)}".encode()).hexdigest()
        with self._lock, self._db:
            row = self._db.execute("SELECT share_id FROM shares WHERE content_hash = ?", (contentHash,)).fetchone()
            if row is not None:
                return self._load(row[0])
            shareId = secrets.token_urlsafe(16)
            createdAt = datetime.now(timezone.utc).replace(microsecond=0)
            self._db.execute(
                "INSERT INTO shares (share_id, content_hash, kind, created_at, memos) VALUES (?, ?, ?, ?, ?)",
                (shareId, contentHash, kind, createdAt.isoformat(), _memoList.dump_json(memos).decode()),
            )
        return ShareView(share_id=shareId, kind=kind, created_at=createdAt, memos=memos)

    def get(self, shareId: str) -> ShareView | None:
        if not SHARE_ID_PATTERN.match(shareId):
            return None
        with self._lock:
            return self._load(shareId)

    def _load(self, shareId: str) -> ShareView | None:
        row = self._db.execute(
            "SELECT kind, created_at, memos FROM shares WHERE share_id = ?", (shareId,)
        ).fetchone()
        if row is None:
            return None
        kind, createdAt, memos = row
        return ShareView(
            share_id=shareId,
            kind=kind,
            created_at=datetime.fromisoformat(createdAt),
            memos=_memoList.validate_json(memos),
        )


_store: ShareStore | None = None
_storeLock = threading.Lock()


def getShareStore() -> ShareStore:
    global _store
    with _storeLock:
        if _store is None:
            _store = ShareStore(os.getenv("SHARE_DB_PATH") or DEFAULT_DB_PATH)
        return _store
