// Types mirror backend/app/models.py.

export type MatchStatus = "matched" | "partial" | "missing";
export type Priority = "high" | "medium" | "low";

export interface Requirement {
  term: string;
  category: string;
  importance: "required" | "preferred";
  status: MatchStatus;
  resume_evidence: string;
  note: string;
}

export interface Highlight {
  experience: string;
  why_relevant: string;
}

export interface Recommendation {
  section: "summary" | "skills" | "experience" | "other";
  priority: Priority;
  suggestion: string;
  rationale: string;
}

export interface RewrittenBullet {
  original: string;
  improved: string;
  keywords_used: string[];
}

export interface ScoreBreakdown {
  score: number;
  matched: number;
  partial: number;
  missing: number;
  explanation: string;
  disclaimer: string;
}

export interface AnalyzeResponse {
  role_title: string;
  score: ScoreBreakdown;
  requirements: Requirement[];
  highlights: Highlight[];
  recommendations: Recommendation[];
  rewritten_bullets: RewrittenBullet[];
}

// Keep in sync with backend/app/models.py.
export const MIN_INPUT_CHARS = 100;
export const MAX_RESUME_CHARS = 30_000;
export const MAX_JOB_DESCRIPTION_CHARS = 20_000;

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function analyzeResume(
  resume: string,
  jobDescription: string,
): Promise<AnalyzeResponse> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/api/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ resume, job_description: jobDescription }),
    });
  } catch {
    throw new Error(`Could not reach the analysis server at ${API_URL}. Is the backend running?`);
  }

  if (!res.ok) {
    throw new Error(await errorMessage(res));
  }
  return res.json();
}

async function errorMessage(res: Response): Promise<string> {
  try {
    const body = await res.json();
    // FastAPI validation errors return a list of {loc, msg}.
    if (Array.isArray(body.detail)) {
      return body.detail
        .map((d: { loc?: string[]; msg: string }) => `${d.loc?.at(-1) ?? "input"}: ${d.msg}`)
        .join("; ");
    }
    if (typeof body.detail === "string") return body.detail;
  } catch {
    // fall through
  }
  return `Request failed (${res.status}). Please try again.`;
}
