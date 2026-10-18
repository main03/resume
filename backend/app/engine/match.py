"""Compare job terms against the resume and produce Requirement objects."""

import re
from dataclasses import dataclass

from ..models import Requirement
from .job import JobTerm, degree_levels
from .resume import LIST_SECTIONS, ResumeProfile, experience_years
from .skills import find_skills, same_wording
from .text import Line, tokens

EVIDENCE_WINDOW = 90  # characters of context on each side of a keyword


@dataclass
class Occurrence:
    line: Line
    surface: str
    start: int
    end: int


@dataclass
class Match:
    """A Requirement plus the details the advice step needs."""
    requirement: Requirement
    term: JobTerm
    reason: str = ""  # "wording" | "listed_only" | ""
    resume_surface: str = ""
    occurrences: list[Occurrence] | None = None


def match_all(terms: list[JobTerm], resume: ResumeProfile) -> list[Match]:
    skill_hits = _index_skills(resume)
    out = []
    for term in terms:
        if term.kind == "skill":
            out.append(_match_skill(term, skill_hits.get(term.skill.name, [])))
        elif term.kind == "acronym":
            out.append(_match_skill(term, _find_exact(term.term, resume)))
        elif term.kind == "years":
            out.append(_match_years(term, resume))
        elif term.kind == "degree":
            out.append(_match_degree(term, resume))
        elif term.kind == "responsibility":
            out.append(_match_responsibility(term, resume))
    return out


def _requirement(term: JobTerm, status: str, evidence: str, note: str) -> Requirement:
    return Requirement(
        term=term.term, category=term.category, importance=term.importance,
        status=status, resume_evidence=evidence, note=note,
    )


def _index_skills(resume: ResumeProfile) -> dict[str, list[Occurrence]]:
    index: dict[str, list[Occurrence]] = {}
    for line in resume.lines:
        for hit in find_skills(line.text):
            index.setdefault(hit.skill.name, []).append(
                Occurrence(line, hit.surface, hit.start, hit.end)
            )
    return index


def _find_exact(word: str, resume: ResumeProfile) -> list[Occurrence]:
    pattern = re.compile(rf"(?<![\w-]){re.escape(word)}(?![\w-])")
    return [
        Occurrence(line, m.group(0), m.start(), m.end())
        for line in resume.lines for m in pattern.finditer(line.text)
    ]


def evidence_snippet(occ: Occurrence) -> str:
    """A verbatim slice of the resume line around the keyword, cut at word boundaries."""
    text = occ.line.text
    if len(text) <= 2 * EVIDENCE_WINDOW:
        return text
    start = max(0, occ.start - EVIDENCE_WINDOW)
    end = min(len(text), occ.end + EVIDENCE_WINDOW)
    if start > 0 and " " in text[start:occ.start]:
        start = text.index(" ", start) + 1
    if end < len(text) and " " in text[occ.end:end]:
        end = text.rindex(" ", occ.end, end)
    return text[start:end]


def _match_skill(term: JobTerm, occurrences: list[Occurrence]) -> Match:
    if not occurrences:
        return Match(_requirement(term, "missing", "", "Not found in your resume."), term)

    synonyms = [o for o in occurrences if not (term.skill and term.skill.is_related(o.surface))]
    if not synonyms:
        occ = occurrences[0]
        note = (
            f"Your resume mentions the related “{occ.surface}”, but the posting asks for "
            f"“{term.term}”. Only use the posting's term if it accurately describes your work."
        )
        return Match(
            _requirement(term, "partial", evidence_snippet(occ), note),
            term, reason="related", resume_surface=occ.surface, occurrences=occurrences,
        )
    occurrences = synonyms

    same = [o for o in occurrences if same_wording(o.surface, term.term)]
    in_context = [o for o in (same or occurrences) if o.line.section not in LIST_SECTIONS]

    if same and in_context:
        occ = in_context[0]
        return Match(
            _requirement(term, "matched", evidence_snippet(occ), _where(occ)),
            term, occurrences=occurrences,
        )
    if not same:
        occ = (in_context or occurrences)[0]
        note = (
            f"Your resume says “{occ.surface}” but the posting says “{term.term}”. "
            "ATS keyword filters often look for the exact wording."
        )
        return Match(
            _requirement(term, "partial", evidence_snippet(occ), note),
            term, reason="wording", resume_surface=occ.surface, occurrences=occurrences,
        )
    occ = same[0]
    note = "Only listed in your skills/education section, not shown in any experience bullet."
    return Match(
        _requirement(term, "partial", evidence_snippet(occ), note),
        term, reason="listed_only", occurrences=occurrences,
    )


def _where(occ: Occurrence) -> str:
    return {
        "experience": "Shown in your work experience.",
        "projects": "Shown in your projects.",
        "summary": "Mentioned in your summary.",
    }.get(occ.line.section, "Found in your resume.")


def _match_years(term: JobTerm, resume: ResumeProfile) -> Match:
    years, line = experience_years(resume)
    if not line:
        note = (
            "Couldn't find date ranges for your roles. List start and end dates "
            "(e.g. “Jan 2021 – Present”) so recruiters and ATS can see your experience."
        )
        return Match(_requirement(term, "partial", "", note), term)
    summary = f"Your listed roles add up to about {years:g} years."
    if years >= term.value:
        return Match(_requirement(term, "matched", line, summary), term)
    if years >= term.value - 1:
        return Match(_requirement(term, "partial", line, summary + " Slightly under the ask."), term)
    return Match(_requirement(term, "missing", "", summary), term)


def _match_degree(term: JobTerm, resume: ResumeProfile) -> Match:
    best_level, best_line = 0, ""
    for line in resume.lines:
        level = max(degree_levels(line.text), default=0)
        if level > best_level:
            best_level, best_line = level, line.text
    if best_level >= term.value:
        return Match(_requirement(term, "matched", best_line, "Degree requirement met."), term)
    equivalent = any("equivalent" in t.lower() for t in term.lines)
    note = "No matching degree found in your resume."
    if equivalent:
        note += " The posting accepts equivalent experience, so highlight that instead."
    if best_level:
        return Match(_requirement(term, "partial", best_line, note), term)
    return Match(_requirement(term, "missing", "", note), term)


def _match_responsibility(term: JobTerm, resume: ResumeProfile) -> Match:
    wanted = tokens(term.lines[0])
    best_score, best_line = 0.0, None
    for line in resume.lines:
        if line.section in LIST_SECTIONS or len(line.text) < 20:
            continue
        score = len(wanted & tokens(line.text)) / max(len(wanted), 1)
        if score > best_score:
            best_score, best_line = score, line
    if best_line and best_score >= 0.5:
        return Match(_requirement(
            term, "matched", best_line.text, "Your experience describes similar work."
        ), term)
    if best_line and best_score >= 0.25:
        return Match(_requirement(
            term, "partial", best_line.text,
            "Some overlap. If accurate, describe this work using the posting's terms.",
        ), term)
    return Match(_requirement(
        term, "missing", "", "No similar work found in your resume."
    ), term)
