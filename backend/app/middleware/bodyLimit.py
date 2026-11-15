from fastapi import Request
from fastapi.responses import JSONResponse

MAX_BODY_BYTES = 512 * 1024


async def limitRequestBody(request: Request, call_next):
    """Refuses oversized POST bodies before FastAPI reads and parses them."""
    if request.method == "POST":
        declared = request.headers.get("content-length")
        if declared is None:
            if request.headers.get("transfer-encoding"):
                return JSONResponse({"detail": "Content-Length required."}, status_code=411)
        elif not declared.isdigit() or int(declared) > MAX_BODY_BYTES:
            return JSONResponse({"detail": "Request body too large."}, status_code=413)
    return await call_next(request)
