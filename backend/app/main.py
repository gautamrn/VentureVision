from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers.analyze import router as analyzeRouter

app = FastAPI(
    title="VentureVision",
    description="Multi-agent due diligence engine",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyzeRouter)


@app.get("/health")
async def health():
    return {"status": "ok"}
