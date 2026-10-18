"""Pydantic models for the API contract and the analysis engine's output."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

MIN_INPUT_CHARS = 100
MAX_RESUME_CHARS = 30_000
MAX_JOB_DESCRIPTION_CHARS = 20_000

Category = Literal[
    "technical_skill", "tool", "qualification", "responsibility", "soft_skill", "domain"
]
Importance = Literal["required", "preferred"]
MatchStatus = Literal["matched", "partial", "missing"]
Section = Literal["summary", "skills", "experience", "other"]
Priority = Literal["high", "medium", "low"]


# ---------- Request ----------


class AnalyzeRequest(BaseModel):
    resume: str = Field(min_length=MIN_INPUT_CHARS, max_length=MAX_RESUME_CHARS)
    job_description: str = Field(
        min_length=MIN_INPUT_CHARS, max_length=MAX_JOB_DESCRIPTION_CHARS
    )

    @field_validator("resume", "job_description", mode="before")
    @classmethod
    def strip_whitespace(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


# ---------- Analysis (engine output) ----------


class Requirement(BaseModel):
    term: str = Field(description="Short keyword or phrase as worded in the job description.")
    category: Category
    importance: Importance
    status: MatchStatus
    resume_evidence: str = Field(
        description="Exact quote copied from the resume that supports the status, or empty string."
    )
    note: str = Field(description="One sentence explaining the status.")


class Highlight(BaseModel):
    experience: str = Field(description="Existing resume content worth emphasizing.")
    why_relevant: str


class Recommendation(BaseModel):
    section: Section
    priority: Priority
    suggestion: str
    rationale: str


class RewrittenBullet(BaseModel):
    original: str = Field(description="The bullet copied exactly from the resume.")
    improved: str
    keywords_used: list[str]


class Analysis(BaseModel):
    role_title: str
    requirements: list[Requirement]
    highlights: list[Highlight]
    recommendations: list[Recommendation]
    rewritten_bullets: list[RewrittenBullet]


# ---------- Response ----------


class ScoreBreakdown(BaseModel):
    score: int = Field(ge=0, le=100)
    matched: int
    partial: int
    missing: int
    explanation: str
    disclaimer: str


class AnalyzeResponse(BaseModel):
    role_title: str
    score: ScoreBreakdown
    requirements: list[Requirement]
    highlights: list[Highlight]
    recommendations: list[Recommendation]
    rewritten_bullets: list[RewrittenBullet]
