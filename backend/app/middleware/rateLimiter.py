import time
import threading

from fastapi import Request, HTTPException

# ── Configuration ──────────────────────────────────────────────
MAX_REQUESTS = 5          # max analyses allowed per window
WINDOW_SECONDS = 3600     # 1 hour sliding window

# ── In-memory store ───────────────────────────────────────────
# Maps IP → list of request timestamps (floats)
_requests: dict[str, list[float]] = {}
_lock = threading.Lock()


async def rateLimitGuard(request: Request) -> None:
    """FastAPI dependency that enforces per-IP rate limiting.

    Raises HTTP 429 if the client has exceeded MAX_REQUESTS
    within the last WINDOW_SECONDS.
    """
    clientIp = request.client.host if request.client else "unknown"
    now = time.time()
    cutoff = now - WINDOW_SECONDS

    with _lock:
        # Get or create timestamp list for this IP
        timestamps = _requests.get(clientIp, [])

        # Prune expired timestamps (outside the sliding window)
        timestamps = [t for t in timestamps if t > cutoff]

        if len(timestamps) >= MAX_REQUESTS:
            # Calculate seconds until the oldest request expires
            retryAfter = int(timestamps[0] - cutoff) + 1
            _requests[clientIp] = timestamps
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Try again in {retryAfter} seconds.",
                headers={"Retry-After": str(retryAfter)},
            )

        # Allow the request — record the timestamp
        timestamps.append(now)
        _requests[clientIp] = timestamps
