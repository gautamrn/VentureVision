import os
import time
import threading

from fastapi import Request, HTTPException

MAX_REQUESTS = 5
WINDOW_SECONDS = 3600
# Number of reverse proxies in front of the app that each append to X-Forwarded-For.
# 0 trusts only the socket peer; entries left of the trusted hops are client-controlled.
TRUSTED_PROXY_HOPS = int(os.getenv("TRUSTED_PROXY_HOPS", "0"))

_requests: dict[str, list[float]] = {}
_lock = threading.Lock()


def clientIpFor(request: Request) -> str:
    peer = request.client.host if request.client else "unknown"
    if TRUSTED_PROXY_HOPS <= 0:
        return peer
    forwarded = [hop.strip() for hop in request.headers.get("x-forwarded-for", "").split(",") if hop.strip()]
    if len(forwarded) < TRUSTED_PROXY_HOPS:
        return peer
    return forwarded[-TRUSTED_PROXY_HOPS]


async def rateLimitGuard(request: Request) -> None:
    clientIp = clientIpFor(request)
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
