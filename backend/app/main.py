"""FastAPI entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import engine
from .config import settings
from .models import AnalyzeRequest, AnalyzeResponse
from .scoring import postprocess

app = FastAPI(title="ATS Resume Optimizer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    analysis = engine.analyze(request.resume, request.job_description)
    return AnalyzeResponse(**postprocess(analysis, request.resume))
