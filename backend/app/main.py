import os

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.middleware.bodyLimit import limitRequestBody
from app.routers.analyze import router as analyzeRouter
from app.routers.feedback import router as feedbackRouter
from app.routers.shares import router as sharesRouter

app = FastAPI(
    title="VentureVision",
    description="Multi-agent due diligence engine",
    version="0.1.0",
)

allowedOrigins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in allowedOrigins],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Admin-Key"],
)


@app.middleware("http")
async def securityHeaders(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response


app.middleware("http")(limitRequestBody)

app.include_router(analyzeRouter)
app.include_router(sharesRouter)
app.include_router(feedbackRouter)


@app.get("/health")
async def health():
    return {"status": "ok"}
