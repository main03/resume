import { AnalyzeResponse, Requirement } from "@/lib/api";
import CopyButton from "./CopyButton";

const SECTION_LABELS = {
  summary: "Summary",
  skills: "Skills",
  experience: "Experience",
  other: "Other",
} as const;

export default function Report({ result }: { result: AnalyzeResponse }) {
  const { score, requirements, highlights, recommendations, rewritten_bullets } = result;
  const matched = requirements.filter((r) => r.status === "matched");
  const partial = requirements.filter((r) => r.status === "partial");
  const missing = requirements.filter((r) => r.status === "missing");
  const allImproved = rewritten_bullets.map((b) => `• ${b.improved}`).join("\n");

  return (
    <div className="report">
      <section className="card score-card">
        <div className={`score-ring ${scoreLevel(score.score)}`}>
          <span className="score-value">{score.score}</span>
          <span className="score-label">match</span>
        </div>
        <div>
          <h2>{result.role_title}</h2>
          <p className="counts">
            <span className="pill matched">{score.matched} matched</span>
            <span className="pill partial">{score.partial} partial</span>
            <span className="pill missing">{score.missing} missing</span>
          </p>
          <p className="muted small-text">
            <strong>How this is calculated:</strong> {score.explanation}
          </p>
          <p className="muted small-text">{score.disclaimer}</p>
        </div>
      </section>

      <div className="grid">
        <KeywordSection
          title="Matched keywords"
          hint="Clearly demonstrated in your resume."
          items={matched}
          tone="matched"
        />
        <KeywordSection
          title="Underrepresented"
          hint="Implied or weakly worded. Make these explicit if accurate."
          items={partial}
          tone="partial"
        />
      </div>

      <KeywordSection
        title="Missing keywords & requirements"
        hint="Not found in your resume. Add them only if you genuinely have the experience; otherwise treat them as real gaps."
        items={missing}
        tone="missing"
      />

      {recommendations.length > 0 && (
        <section className="card">
          <h3>Recommended changes</h3>
          <ol className="recommendations">
            {recommendations.map((r, i) => (
              <li key={i}>
                <div className="rec-head">
                  <span className={`pill priority-${r.priority}`}>{r.priority}</span>
                  <span className="pill neutral">{SECTION_LABELS[r.section]}</span>
                </div>
                <p>{r.suggestion}</p>
                {r.rationale && <p className="muted small-text">{r.rationale}</p>}
              </li>
            ))}
          </ol>
        </section>
      )}

      {highlights.length > 0 && (
        <section className="card">
          <h3>Relevant experience to highlight</h3>
          <ul className="plain-list">
            {highlights.map((h, i) => (
              <li key={i}>
                <p>{h.experience}</p>
                <p className="muted small-text">{h.why_relevant}</p>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="card">
        <div className="section-head">
          <h3>Improved bullet points</h3>
          {rewritten_bullets.length > 0 && <CopyButton text={allImproved} label="Copy all" />}
        </div>
        <p className="muted small-text">
          Your bullets with the job&apos;s exact wording swapped in where your resume uses a
          true synonym (e.g. k8s → Kubernetes). Nothing new is added.
        </p>
        {rewritten_bullets.length === 0 ? (
          <p className="muted">
            No wording swaps needed: your bullets already use the posting&apos;s terms where they
            overlap.
          </p>
        ) : (
          <ul className="bullets">
            {rewritten_bullets.map((b, i) => (
              <li key={i}>
                <p className="original">
                  <span className="tag">Before</span> {b.original}
                </p>
                <div className="improved-row">
                  <p className="improved">
                    <span className="tag">After</span> {b.improved}
                  </p>
                  <CopyButton text={b.improved} />
                </div>
                {b.keywords_used.length > 0 && (
                  <p className="keywords-used">
                    {b.keywords_used.map((k) => (
                      <span key={k} className="chip">
                        {k}
                      </span>
                    ))}
                  </p>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function KeywordSection({
  title,
  hint,
  items,
  tone,
}: {
  title: string;
  hint: string;
  items: Requirement[];
  tone: "matched" | "partial" | "missing";
}) {
  return (
    <section className="card">
      <h3>
        {title} <span className="muted">({items.length})</span>
      </h3>
      <p className="muted small-text">{hint}</p>
      {items.length === 0 ? (
        <p className="muted">None.</p>
      ) : (
        <ul className="keywords">
          {items.map((r, i) => (
            <li key={`${r.term}-${i}`} className={`keyword ${tone}`}>
              <div className="keyword-head">
                <strong>{r.term}</strong>
                {r.importance === "required" && <span className="pill neutral">required</span>}
                <span className="category">{r.category.replace("_", " ")}</span>
              </div>
              {r.note && <p className="small-text">{r.note}</p>}
              {r.resume_evidence && (
                <blockquote className="small-text">“{r.resume_evidence}”</blockquote>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function scoreLevel(score: number): string {
  if (score >= 75) return "high";
  if (score >= 50) return "mid";
  return "low";
}
