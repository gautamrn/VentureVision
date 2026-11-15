import hashlib
import hmac
import json
import logging
import os
import secrets
from datetime import datetime, timezone
from functools import lru_cache

from app.schemas.models import MemoOutput, SealedMemo, ShareSeal

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def signingKey() -> bytes:
    configured = os.getenv("SHARE_SIGNING_KEY", "")
    if configured:
        return configured.encode()
    # Without a configured key, memos sealed before a restart can no longer be shared.
    logger.warning("SHARE_SIGNING_KEY is not set; using a per-process key")
    return secrets.token_bytes(32)


def canonicalBytes(pitch: str, mode: str, generatedAt: datetime, memo: MemoOutput) -> bytes:
    body = {
        "pitch": pitch,
        "mode": mode,
        "generated_at": generatedAt.astimezone(timezone.utc).isoformat(),
        "memo": memo.model_dump(mode="json"),
    }
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sign(pitch: str, mode: str, generatedAt: datetime, memo: MemoOutput) -> str:
    return hmac.new(signingKey(), canonicalBytes(pitch, mode, generatedAt, memo), hashlib.sha256).hexdigest()


def sealMemo(pitch: str, mode: str, memo: MemoOutput) -> ShareSeal:
    generatedAt = datetime.now(timezone.utc).replace(microsecond=0)
    return ShareSeal(generated_at=generatedAt, signature=sign(pitch, mode, generatedAt, memo))


def verifySeal(sealed: SealedMemo) -> bool:
    expected = sign(sealed.pitch, sealed.mode, sealed.seal.generated_at, sealed.memo)
    return hmac.compare_digest(expected, sealed.seal.signature)
