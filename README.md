# ATS Resume Optimizer

Paste a resume and a job description. The app finds which job requirements the resume
already covers, which are underrepresented or missing, and suggests truthful
improvements, including ATS-friendly wording for existing bullets.

Everything runs locally with a custom rule-based analysis engine. There are no external
APIs, no API keys, and no database. Nothing you paste is stored or sent anywhere.

## Architecture

```
frontend/  Next.js + React + TypeScript (single page)
  app/page.tsx            inputs, loading/error state
  components/Report.tsx   score, keyword sections, recommendations, bullet rewrites
  lib/api.ts              API types + fetch client

backend/   FastAPI + Pydantic
  app/main.py             POST /api/analyze, GET /api/health
  app/models.py           request/response + analysis schemas
  app/engine/             analysis engine
    job.py                job description -> requirements (sections, required/preferred)
    resume.py             resume sections + years of experience from date ranges
    skills.py             keyword search over data/skills.json
    match.py              matched / partial / missing per requirement
    advice.py             recommendations, highlights, wording-swap rewrites
    text.py               shared text helpers (sections, tokens, stemming)
  app/data/skills.json    skills dictionary with synonyms (edit to extend)
  app/scoring.py          evidence verification + deterministic score
  tests/                  pytest
```

Flow: frontend → `POST /api/analyze` → the engine produces an analysis → `scoring.py`
verifies it and computes the score → frontend renders the report.

## How the engine works

1. **Job description.** Detects sections ("Requirements", "Nice to have",
   "Responsibilities"; "About us" and "Benefits" are ignored, so the company's own tech
   stack isn't mistaken for a requirement). Each keyword is marked required or preferred
   from its section and cues like "a plus" or "must". It also extracts years of
   experience, degree level, unknown acronyms (e.g. HIPAA) and responsibility bullets.
2. **Resume.** Splits into sections (Summary, Experience, Skills, Education…) and adds up
   the date ranges of your roles, merging overlaps. Markdown `**bold**` and Unicode bold
   letters (𝐏𝐲𝐭𝐡𝐨𝐧) are normalized before matching.
3. **Matching.**
   - **matched:** the posting's wording appears in your experience, projects or summary.
   - **partial:** the term appears only in a skills list, under a synonym (k8s vs
     Kubernetes), or as a related term (CI vs CI/CD).
   - **missing:** not found.

   Responsibilities are matched by word overlap with your bullets. Because that is
   approximate, they always count as preferred (1×) in the score.
4. **Advice.** Prioritized recommendations for the summary, skills and experience
   sections, plus resume-quality checks: weak openers ("Responsible for…"), bullets
   without numbers, Unicode "bold" letters ATS can't read, and a missing skills section.

### Truthful rewrites

Rewrites only swap the posting's wording in for **true synonyms** that your bullet
already uses, e.g. `Deployed services to k8s` → `Deployed services to Kubernetes (k8s)`.
They never add skills, achievements or numbers. Related-but-different terms (CI vs CI/CD,
Spring vs Spring Boot) get partial credit and an "only if accurate" note, but are never
swapped in automatically.

### Extending the skills dictionary

The engine recognizes skills listed in `backend/app/data/skills.json`, plus acronyms it
finds in the posting. To support a new skill, add it under a category:

```json
"tool": {
  "Kubernetes": ["k8s"],
  "=Excel": ["Microsoft Excel"],
  "CI/CD": ["~=CI", "~continuous integration"]
}
```

- A plain alias is a true synonym and may be swapped into rewrites.
- `=` means case-sensitive, for words that are also common English (Go, Excel, Spring).
- `~` means a related term, not a synonym: it earns partial credit but is never swapped.

## How the match score works

Each requirement is labelled `matched`, `partial` or `missing`, with a supporting quote
from the resume. The backend then:

1. **Verifies evidence.** A quote not found in the resume is discarded, and a "matched"
   item without verifiable evidence is downgraded to "partial".
2. **Drops invalid rewrites.** A bullet rewrite whose original isn't actually in the
   resume is removed.
3. **Scores deterministically.** `score = Σ(weight × credit) / Σ weight × 100`, with
   required = 3, preferred = 1, matched = 1, partial = 0.5, missing = 0.

The score measures keyword and requirement coverage only. It does not guarantee an
interview or shortlisting.

## Running locally

Requirements: Python 3.12+ with [uv](https://docs.astral.sh/uv/) and Node 20+.

**Backend** (port 8000):

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

**Frontend** (port 3000):

```bash
cd frontend
cp .env.local.example .env.local   # only needed if the backend isn't on localhost:8000
npm install
npm run dev
```

Open http://localhost:3000.

### Configuration

| Where | Variable | Default | Notes |
|---|---|---|---|
| `backend/.env` | `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated frontend origins. |
| `frontend/.env.local` | `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend URL. |

## Tests

```bash
cd backend && uv run pytest
cd frontend && npm run typecheck
```

## Input limits

Resume: 100–30,000 characters. Job description: 100–20,000 characters. These are
enforced in both the UI and the API (`app/models.py`).

## Known limitations

- Skills outside `skills.json` are only detected if they're acronyms (e.g. HIPAA). Add
  domain-specific terms to the dictionary for best results.
- Responsibility matching uses word overlap, so it's an approximation.
- Rewrites are limited to wording swaps; the engine doesn't write new bullets.
