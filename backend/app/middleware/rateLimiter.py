import time
import threading

from fastapi import Request, HTTPException

MAX_REQUESTS = 5
WINDOW_SECONDS = 3600

_requests: dict[str, list[float]] = {}
_lock = threading.Lock()


async def rateLimitGuard(request: Request) -> None:
    clientIp = request.client.host if request.client else "unknown"
    now = time.time()
    cutoff = now - WINDOW_SECONDS

    with _lock:
        timestamps = _requests.get(clientIp, [])
        timestamps = [t for t in timestamps if t > cutoff]

        if len(timestamps) >= MAX_REQUESTS:
            retryAfter = int(timestamps[0] - cutoff) + 1
            _requests[clientIp] = timestamps
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Try again in {retryAfter} seconds.",
                headers={"Retry-After": str(retryAfter)},
            )

        timestamps.append(now)
        _requests[clientIp] = timestamps
