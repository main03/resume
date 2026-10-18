"use client";

import { useState } from "react";
import {
  analyzeResume,
  AnalyzeResponse,
  MAX_JOB_DESCRIPTION_CHARS,
  MAX_RESUME_CHARS,
  MIN_INPUT_CHARS,
} from "@/lib/api";
import TextInput from "@/components/TextInput";
import Report from "@/components/Report";

export default function Home() {
  const [resume, setResume] = useState("");
  const [jobDescription, setJobDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);

  const validationError = validate(resume, jobDescription);

  async function handleAnalyze() {
    if (validationError) {
      setError(validationError);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setResult(await analyzeResume(resume.trim(), jobDescription.trim()));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="container">
      <header className="page-header">
        <h1>ATS Resume Optimizer</h1>
        <p className="muted">
          Paste your resume and a job description to see which requirements you already
          cover, what&apos;s missing, and how to improve your resume truthfully.
        </p>
      </header>

      <section className="inputs">
        <TextInput
          id="resume"
          label="Your resume"
          placeholder="Paste your resume as plain text…"
          value={resume}
          onChange={setResume}
          maxLength={MAX_RESUME_CHARS}
        />
        <TextInput
          id="job"
          label="Job description"
          placeholder="Paste the full job description…"
          value={jobDescription}
          onChange={setJobDescription}
          maxLength={MAX_JOB_DESCRIPTION_CHARS}
        />
      </section>

      <div className="actions">
        <button className="primary" onClick={handleAnalyze} disabled={loading}>
          {loading ? "Analyzing…" : "Analyze Resume"}
        </button>
        {loading && (
          <span className="muted loading">
            <span className="spinner" aria-hidden /> Comparing your resume with the job
            description…
          </span>
        )}
      </div>

      {error && (
        <div className="error" role="alert">
          {error}
        </div>
      )}

      {result && !loading && <Report result={result} />}
    </main>
  );
}

function validate(resume: string, jobDescription: string): string | null {
  if (resume.trim().length < MIN_INPUT_CHARS)
    return `Your resume looks too short. Paste at least ${MIN_INPUT_CHARS} characters.`;
  if (jobDescription.trim().length < MIN_INPUT_CHARS)
    return `The job description looks too short. Paste at least ${MIN_INPUT_CHARS} characters.`;
  return null;
}
