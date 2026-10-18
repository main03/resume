"""Rule-based resume analyzer. Runs fully offline.

Pipeline: parse the job description into terms (job.py) -> parse the resume into sections
(resume.py) -> match each term (match.py) -> derive advice (advice.py).
"""

from ..models import Analysis
from .advice import highlights, recommendations, rewrites
from .job import parse_job
from .match import match_all
from .resume import parse_resume


def analyze(resume: str, job_description: str) -> Analysis:
    job = parse_job(job_description)
    profile = parse_resume(resume)
    matches = match_all(job.terms, profile)
    return Analysis(
        role_title=job.role_title,
        requirements=[m.requirement for m in matches],
        highlights=highlights(matches),
        recommendations=recommendations(matches, profile, resume, job.role_title),
        rewritten_bullets=rewrites(matches),
    )
