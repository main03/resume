"""Turn match results into highlights, recommendations and bullet rewrites."""

import re

from ..models import Highlight, Recommendation, RewrittenBullet
from .match import Match
from .resume import LIST_SECTIONS, ResumeProfile

KEYWORD_CATEGORIES = {"technical_skill", "tool", "domain", "soft_skill"}
SWAPPABLE = {"technical_skill", "tool", "domain", "qualification"}
WEAK_OPENERS = re.compile(
    r"^(responsible for|worked on|helped( with)?|assisted( with| in)?|involved in|tasked with"
    r"|duties included|participated in)\b",
    re.IGNORECASE,
)
MAX_REWRITES = 6
MAX_HIGHLIGHTS = 4


def _join(items: list[str], limit: int = 8) -> str:
    items = items[:limit]
    return ", ".join(f"“{i}”" for i in items)


def _is_statement(line) -> bool:
    """A bullet or sentence describing work, as opposed to a heading, list or contact line.
    Bullet markers are often lost when copying from a PDF, so long lines count too."""
    return line.section not in LIST_SECTIONS and (line.is_bullet or len(line.text) >= 40)


# ---------- Highlights ----------


def highlights(matches: list[Match]) -> list[Highlight]:
    """Resume lines that already demonstrate several required keywords."""
    by_line: dict[str, list[str]] = {}
    for m in matches:
        r = m.requirement
        if r.status == "matched" and r.importance == "required" and r.category in KEYWORD_CATEGORIES:
            by_line.setdefault(r.resume_evidence, []).append(r.term)
    ranked = sorted(by_line.items(), key=lambda kv: -len(kv[1]))[:MAX_HIGHLIGHTS]
    return [
        Highlight(
            experience=line,
            why_relevant=(
                f"Demonstrates {_join(terms)}, required for this role. Keep this bullet "
                "near the top of the role so it's seen first."
            ),
        )
        for line, terms in ranked
    ]


# ---------- Recommendations ----------


def recommendations(
    matches: list[Match], resume: ResumeProfile, resume_text: str, role_title: str
) -> list[Recommendation]:
    recs: list[Recommendation] = []
    reqs = [m.requirement for m in matches]

    def keywords(status: str, importance: str) -> list[str]:
        return [
            m.requirement.term for m in matches
            if m.term.kind in ("skill", "acronym")
            and m.requirement.status == status and m.requirement.importance == importance
        ]

    missing_required = keywords("missing", "required")
    if missing_required:
        recs.append(Recommendation(
            section="skills", priority="high",
            suggestion=(
                f"Required keywords missing from your resume: {_join(missing_required)}. If you "
                "genuinely have this experience, add each to your skills section and to the "
                "experience bullet where you used it."
            ),
            rationale=(
                "Required skills are what ATS filters and recruiters screen for first. If you "
                "don't have them, treat them as real gaps: address them in a cover letter or "
                "by building the skill. Don't add skills you can't back up."
            ),
        ))

    wording = [m for m in matches if m.reason == "wording"]
    if wording:
        pairs = "; ".join(
            f"“{m.requirement.term}” instead of “{m.resume_surface}”" for m in wording[:6]
        )
        recs.append(Recommendation(
            section="skills", priority="high",
            suggestion=f"Use the posting's exact wording: {pairs}.",
            rationale=(
                "Many ATS match keywords literally, so a synonym may not count. Writing both "
                "forms, e.g. “Kubernetes (k8s)”, covers either search."
            ),
        ))

    related = [m for m in matches if m.reason == "related"]
    if related:
        pairs = "; ".join(
            f"“{m.requirement.term}” (you wrote “{m.resume_surface}”)" for m in related[:6]
        )
        recs.append(Recommendation(
            section="experience", priority="medium",
            suggestion=(
                f"Your resume mentions related experience for: {pairs}. If your work truly "
                "covered the posting's term, say so explicitly; otherwise leave it as is."
            ),
            rationale=(
                "These aren't exact synonyms (e.g. CI isn't the same as CI/CD), so they're "
                "not rewritten automatically."
            ),
        ))

    listed_only = [m.requirement.term for m in matches if m.reason == "listed_only"]
    if listed_only:
        recs.append(Recommendation(
            section="experience", priority="medium",
            suggestion=(
                f"Show {_join(listed_only)} in your experience bullets. Right now they only "
                "appear in a list. Mention each in the bullet describing where you actually "
                "used it."
            ),
            rationale="Skills demonstrated in context carry more weight than a bare list.",
        ))

    for m in matches:
        r = m.requirement
        if m.term.kind in ("years", "degree") and r.status != "matched":
            recs.append(Recommendation(
                section="other", priority="medium",
                suggestion=f"{r.term}: {r.note}",
                rationale=(
                    "If you have relevant experience or education that isn't on your resume "
                    "(freelance, internships, part-time study), add it with dates."
                ),
            ))

    recs.append(_summary_recommendation(reqs, resume, role_title))

    missing_resp = [
        m.requirement.term for m in matches
        if m.term.kind == "responsibility" and m.requirement.status == "missing"
    ]
    if missing_resp:
        recs.append(Recommendation(
            section="experience", priority="medium",
            suggestion=(
                "The role emphasizes work your resume doesn't describe: "
                + "; ".join(f"“{t}”" for t in missing_resp[:3])
                + ". If you've done similar work, add a bullet about it using similar language."
            ),
            rationale="Mirroring the posting's responsibilities helps recruiters map your experience to the role.",
        ))

    missing_preferred = keywords("missing", "preferred")
    if missing_preferred:
        recs.append(Recommendation(
            section="skills", priority="low",
            suggestion=f"Nice-to-haves you could add if you have them: {_join(missing_preferred)}.",
            rationale="Preferred skills aren't deal-breakers, but they can set you apart.",
        ))

    recs.extend(_quality_recommendations(resume, resume_text))
    return recs


def _summary_recommendation(reqs, resume: ResumeProfile, role_title: str) -> Recommendation:
    strongest = [
        r.term for r in reqs
        if r.status == "matched" and r.importance == "required"
        and r.category in {"technical_skill", "tool", "domain"}
    ][:4]
    skills_part = f" and lead with your strongest matching skills ({', '.join(strongest)})" if strongest else ""
    title = f"“{role_title}”" if role_title != "This role" else "the role you're applying for"
    if resume.has_section("summary"):
        suggestion = f"Tailor your summary: name {title}{skills_part}."
    else:
        suggestion = f"Add a 2–3 line summary at the top that names {title}{skills_part}."
    return Recommendation(
        section="summary", priority="medium", suggestion=suggestion,
        rationale="The summary is the first thing a recruiter reads and a common ATS keyword zone.",
    )


def _quality_recommendations(resume: ResumeProfile, resume_text: str) -> list[Recommendation]:
    recs = []
    if resume.has_sections and not resume.has_section("skills"):
        recs.append(Recommendation(
            section="skills", priority="medium",
            suggestion="Add a dedicated “Skills” section listing the tools and technologies you use.",
            rationale="ATS parsers look for a skills section to extract keywords from.",
        ))

    if any(0x1D400 <= ord(ch) <= 0x1D7FF for ch in resume_text):
        recs.append(Recommendation(
            section="other", priority="high",
            suggestion=(
                "Your resume uses special Unicode “bold” letters (like 𝐭𝐡𝐢𝐬). Replace them with "
                "normal text and apply bold with your editor's formatting instead."
            ),
            rationale="Many ATS read these as symbols, so the words inside them won't match any keyword.",
        ))
    elif re.search(r"\*\*[^*\n]+\*\*|__[^_\n]+__", resume_text):
        recs.append(Recommendation(
            section="other", priority="low",
            suggestion=(
                "Your resume text contains Markdown markers (**like this**). If they're in your "
                "actual resume file, remove them and use real bold formatting."
            ),
            rationale="ATS and recruiters see literal asterisks, which looks unpolished.",
        ))

    bullets = [ln for ln in resume.lines if _is_statement(ln) and ln.section != "summary"]
    weak = [ln for ln in bullets if WEAK_OPENERS.match(ln.text)]
    if weak:
        recs.append(Recommendation(
            section="experience", priority="low",
            suggestion=(
                f"{len(weak)} bullet(s) start with weak phrases like “{WEAK_OPENERS.match(weak[0].text).group(0)}”. "
                "Start with an action verb instead, e.g. “Responsible for managing deployments” → "
                "“Managed deployments”."
            ),
            rationale="Action verbs make your contribution clearer to recruiters.",
        ))

    if len(bullets) >= 3:
        without_numbers = [ln for ln in bullets if not re.search(r"\d", ln.text)]
        if len(without_numbers) / len(bullets) > 0.6:
            recs.append(Recommendation(
                section="experience", priority="low",
                suggestion=(
                    "Most of your bullets have no numbers. Where you know them, add real results "
                    "(users served, time saved, % improvement, team size)."
                ),
                rationale="Concrete results are more convincing, but only use figures you can stand behind. Never estimate or invent them.",
            ))
    return recs


# ---------- Rewrites ----------


def _replacement(job_term: str, resume_surface: str) -> str:
    def is_acronym(s: str) -> bool:
        return s.isupper() and len(s) <= 6
    if is_acronym(resume_surface) and not is_acronym(job_term):
        return f"{job_term} ({resume_surface})"
    if is_acronym(job_term) and not is_acronym(resume_surface):
        return f"{resume_surface} ({job_term})"
    if resume_surface.lower() in {"k8s", "postgres", "mongo", "js"}:
        return f"{job_term} ({resume_surface})"
    return job_term


def rewrites(matches: list[Match]) -> list[RewrittenBullet]:
    """Swap the posting's wording into bullets that already use a synonym.

    These rewrites can't add anything untrue: they only rename what the bullet already says.
    """
    edits: dict[int, tuple[str, list[tuple[int, int, str]], list[str]]] = {}
    for m in matches:
        # Only swap true synonyms of concrete skills; never related terms or soft skills.
        if m.reason != "wording" or not m.occurrences or m.term.category not in SWAPPABLE:
            continue
        if m.term.skill and m.term.skill.is_related(m.requirement.term):
            continue
        for occ in m.occurrences:
            if not _is_statement(occ.line):
                continue
            key = id(occ.line)
            text, spans, used = edits.setdefault(key, (occ.line.text, [], []))
            if any(occ.start < e and s < occ.end for s, e, _ in spans):
                continue
            spans.append((occ.start, occ.end, _replacement(m.requirement.term, occ.surface)))
            used.append(m.requirement.term)

    out = []
    for text, spans, used in edits.values():
        improved = text
        for start, end, repl in sorted(spans, reverse=True):
            improved = improved[:start] + repl + improved[end:]
        out.append(RewrittenBullet(original=text, improved=improved, keywords_used=list(dict.fromkeys(used))))
        if len(out) == MAX_REWRITES:
            break
    return out
