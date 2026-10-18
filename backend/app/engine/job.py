"""Extract requirements from a job description."""

import re
from dataclasses import dataclass, field

from .skills import Skill, find_skills, known_terms_lower
from .text import Line, split_sections

JD_HEADERS = {
    # Order matters: "Preferred Qualifications" must hit "preferred" before "qualification".
    "ignore": [
        "about us", "about the company", "who we are", "benefits", "perks", "what we offer",
        "compensation", "salary", "equal opportunity", "eeo", "our values", "why join",
        "why you'll love", "life at", "diversity", "how to apply", "our mission",
    ],
    "preferred": [
        "nice to have", "preferred", "bonus", "plus", "good to have", "desired", "desirable",
        "extra credit", "ideally",
    ],
    "responsibility": [
        "responsibilit", "what you'll do", "what you will do", "what youll do", "the role",
        "your role", "duties", "day to day", "in this role", "your impact", "you will",
        "what you'll be doing",
    ],
    "required": [
        "requirement", "qualification", "must have", "what you need", "what you'll need",
        "what you bring", "what you'll bring", "looking for", "about you", "you have",
        "you are", "skills", "experience", "who you are", "minimum", "basic", "essential",
        "ideal candidate",
    ],
}

PREFERRED_CUES = re.compile(
    r"\b(nice[\s-]to[\s-]have|preferred|a plus|bonus|ideally|desirable|desired|advantage"
    r"|good to have|familiarity with|exposure to)\b",
    re.IGNORECASE,
)
REQUIRED_CUES = re.compile(
    r"\b(must|required|requirement|minimum|at least|essential|mandatory)\b", re.IGNORECASE
)
YEARS_RE = re.compile(
    r"(\d{1,2})\s*\+?\s*(?:(?:-|–|to)\s*\d{1,2}\s*)?\+?\s*(?:years?|yrs?)\b", re.IGNORECASE
)
DEGREE_PATTERNS = {
    # Abbreviations are case-sensitive so "ms" in "100ms" or "ba" in words never match.
    1: re.compile(
        r"(?i:bachelor|undergraduate degree)"
        r"|(?<![A-Za-z0-9])(?:B\.S\.?|BS|BSc|B\.Sc\.?|B\.A\.?|BA|B\.E\.|BEng|B\.?Tech)(?![A-Za-z])",
    ),
    2: re.compile(
        r"(?i:master'?s(?:\s+degree)?\b)"
        r"|(?<![A-Za-z0-9])(?:M\.S\.?|MS|MSc|M\.Sc\.?|MBA|M\.?Tech|MEng|M\.A\.)(?![A-Za-z])"
        r"(?!\s*(?:Office|Excel|Word|SQL|Teams|Azure|Project))",
    ),
    3: re.compile(r"ph\.?\s?d|doctorate|doctoral", re.IGNORECASE),
}
DEGREE_NAMES = {1: "Bachelor's degree", 2: "Master's degree", 3: "PhD"}
GENERIC_DEGREE = re.compile(r"\bdegree\b", re.IGNORECASE)

ACRONYM_RE = re.compile(r"(?<![\w-])[A-Z][A-Z0-9]{1,5}(?![\w-])")
ACRONYM_STOPLIST = {
    "US", "USA", "UK", "EU", "EEO", "EOE", "HR", "PTO", "CEO", "CTO", "CFO", "COO", "VP",
    "LLC", "INC", "LTD", "FAQ", "ID", "OK", "TBD", "ASAP", "NYC", "SF", "LA", "UTC", "PST",
    "EST", "CET", "GMT", "WFH", "DEI", "LGBTQ", "LGBT", "IT", "OR", "AND", "THE", "TO", "IN",
    "OF", "FOR", "WE", "YOU", "OUR", "ON", "AT", "BY", "IS", "AS", "AN", "NOT", "ALL", "NEW",
    "JD", "PM", "AM", "USD", "EUR", "GBP", "K", "II", "III", "IV", "MBA", "BS", "BA", "MS",
    "PHD", "MSC", "BSC", "ADA", "401K", "OTE", "QA", "ETC",
}

MAX_SKILLS = 25
MAX_ACRONYMS = 6
MAX_RESPONSIBILITIES = 6


@dataclass
class JobTerm:
    kind: str  # "skill" | "acronym" | "years" | "degree" | "responsibility"
    term: str  # wording used by the job description
    category: str
    importance: str
    skill: Skill | None = None
    value: int = 0  # years or degree level
    count: int = 1
    order: int = 0
    lines: list[str] = field(default_factory=list)


@dataclass
class JobProfile:
    role_title: str
    terms: list[JobTerm]


def _is_heading_candidate(text: str) -> bool:
    return not find_skills(text)


def _importance(line: Line) -> str:
    if PREFERRED_CUES.search(line.text):
        return "preferred"
    if REQUIRED_CUES.search(line.text):
        return "required"
    return "preferred" if line.section == "preferred" else "required"


def parse_job(job_description: str) -> JobProfile:
    lines = [
        ln for ln in split_sections(
            job_description, JD_HEADERS, default="general",
            is_header_candidate=_is_heading_candidate,
        )
        if ln.section != "ignore"
    ]
    terms = [
        *_skill_terms(lines),
        *_acronym_terms(lines),
        *_years_terms(lines),
        *_degree_terms(lines),
        *_responsibility_terms(lines),
    ]
    return JobProfile(role_title=_role_title(job_description), terms=terms)


def _skill_terms(lines: list[Line]) -> list[JobTerm]:
    by_name: dict[str, JobTerm] = {}
    for i, line in enumerate(lines):
        importance = _importance(line)
        for hit in find_skills(line.text):
            term = by_name.get(hit.skill.name)
            if term is None:
                by_name[hit.skill.name] = JobTerm(
                    "skill", hit.surface, hit.skill.category, importance, hit.skill, order=i
                )
            else:
                term.count += 1
                if importance == "required":
                    term.importance = "required"
    ranked = sorted(
        by_name.values(),
        key=lambda t: (t.importance != "required", -t.count, t.order),
    )
    return ranked[:MAX_SKILLS]


def _acronym_terms(lines: list[Line]) -> list[JobTerm]:
    known = known_terms_lower()
    found: dict[str, JobTerm] = {}
    for i, line in enumerate(lines):
        if line.text.isupper():  # shouty headings, not keywords
            continue
        # Skip pieces of known terms, e.g. "CI" in "CI/CD" or "DSS" in "PCI DSS".
        skill_spans = [(h.start, h.end) for h in find_skills(line.text)]
        for m in ACRONYM_RE.finditer(line.text):
            word = m.group(0)
            if word in ACRONYM_STOPLIST or word.lower() in known or not re.search("[A-Z]{2}", word):
                continue
            if any(s <= m.start() < e for s, e in skill_spans):
                continue
            if word in found:
                found[word].count += 1
            else:
                found[word] = JobTerm("acronym", word, "domain", _importance(line), order=i)
    ranked = sorted(found.values(), key=lambda t: (-t.count, t.order))
    return ranked[:MAX_ACRONYMS]


def _years_terms(lines: list[Line]) -> list[JobTerm]:
    best: JobTerm | None = None
    for line in lines:
        if "experience" not in line.text.lower():
            continue
        for m in YEARS_RE.finditer(line.text):
            years = int(m.group(1))
            if not 0 < years <= 20:
                continue
            importance = _importance(line)
            better = best is None or (importance, years) > (best.importance, best.value)
            # "required" > "preferred" alphabetically, so tuple comparison prefers required.
            if better:
                best = JobTerm(
                    "years", f"{years}+ years of experience", "qualification", importance,
                    value=years, lines=[line.text],
                )
    return [best] if best else []


def degree_levels(text: str) -> list[int]:
    """Degree levels mentioned in text (1 = bachelor, 2 = master, 3 = PhD)."""
    return [lvl for lvl, pattern in DEGREE_PATTERNS.items() if pattern.search(text)]


def _degree_terms(lines: list[Line]) -> list[JobTerm]:
    for line in lines:
        # "Bachelor's or Master's" -> the minimum the posting accepts.
        level = min(degree_levels(line.text), default=0)
        if not level and GENERIC_DEGREE.search(line.text) and re.search(
            r"(bachelor|college|university|computer science|related field|equivalent)",
            line.text, re.IGNORECASE,
        ):
            level = 1
        if level:
            return [JobTerm(
                "degree", DEGREE_NAMES[level], "qualification", _importance(line),
                value=level, lines=[line.text],
            )]
    return []


def _responsibility_terms(lines: list[Line]) -> list[JobTerm]:
    out = []
    for line in lines:
        if line.section == "responsibility" and len(line.text) >= 25:
            out.append(JobTerm(
                "responsibility", _shorten(line.text), "responsibility", "preferred",
                lines=[line.text],
            ))
        if len(out) == MAX_RESPONSIBILITIES:
            break
    return out


def _shorten(text: str, limit: int = 90) -> str:
    text = text.rstrip(".;")
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "…"


TITLE_LABEL = re.compile(r"^(?:job\s+title|position|role|title)\s*:\s*(.+)$", re.IGNORECASE)
HIRING = re.compile(
    r"(?:looking for|hiring|seeking)\s+(?:an?\s+)?((?:[A-Z][\w+#/.-]*\s?){1,6})"
)


def _role_title(job_description: str) -> str:
    raw_lines = [ln.strip() for ln in job_description.splitlines() if ln.strip()]
    for line in raw_lines[:10]:
        if m := TITLE_LABEL.match(line):
            return m.group(1).strip()
    if raw_lines:
        first = raw_lines[0]
        if len(first.split()) <= 8 and not first.endswith((".", ":")) and not re.match(
            r"(about|who|we|our|job description)\b", first, re.IGNORECASE
        ):
            return first
    if m := HIRING.search(job_description):
        return m.group(1).strip()
    return "This role"
