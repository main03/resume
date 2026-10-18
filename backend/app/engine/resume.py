"""Parse a resume into sections and estimate years of experience."""

import re
from dataclasses import dataclass
from datetime import date

from .text import Line, split_sections

RESUME_HEADERS = {
    "summary": ["summary", "profile", "objective", "about me", "about"],
    "skills": [
        "skills", "skill", "competencies", "technologies", "technology", "tools", "tech stack",
        "expertise", "languages", "proficiencies", "toolkit",
    ],
    "experience": ["experience", "employment", "history", "positions", "internships"],
    "projects": ["projects", "project", "portfolio"],
    "education": ["education", "academics", "coursework"],
    "certifications": [
        "certifications", "certification", "certificates", "licenses", "licences", "courses",
        "training",
    ],
    "other": [
        "awards", "honors", "honours", "publications", "interests", "hobbies", "volunteer",
        "volunteering", "references", "activities", "achievements", "leadership",
    ],
}

# Sections where a keyword is only listed rather than shown in context.
LIST_SECTIONS = {"skills", "education"}

_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1
)}
_DATE = r"(?:(?P<{p}m>[A-Za-z]{{3,9}})\.?\s+|(?P<{p}n>\d{{1,2}})/)?(?P<{p}y>(?:19|20)\d{{2}})"
DATE_RANGE = re.compile(
    _DATE.format(p="s")
    + r"\s*(?:-|–|—|to|until)\s*(?:"
    + _DATE.format(p="e")
    + r"|(?P<present>present|current|now|today|ongoing))",
    re.IGNORECASE,
)


@dataclass
class ResumeProfile:
    lines: list[Line]
    has_sections: bool

    def has_section(self, name: str) -> bool:
        return any(ln.section == name for ln in self.lines)


def parse_resume(resume: str) -> ResumeProfile:
    lines = split_sections(resume, RESUME_HEADERS, default="general", strict=True)
    return ResumeProfile(lines, has_sections=any(ln.section != "general" for ln in lines))


def _month_index(match: re.Match, prefix: str) -> int | None:
    year = match.group(f"{prefix}y")
    if not year:
        return None
    month_name = match.group(f"{prefix}m")
    month_num = match.group(f"{prefix}n")
    month = 6  # year only: assume mid-year
    if month_name and month_name[:3].lower() in _MONTHS:
        month = _MONTHS[month_name[:3].lower()]
    elif month_num and 1 <= int(month_num) <= 12:
        month = int(month_num)
    return int(year) * 12 + month - 1


def experience_years(profile: ResumeProfile, today: date | None = None) -> tuple[float, str | None]:
    """Total years covered by date ranges in work sections (overlaps merged).

    Returns (years, first line with a date range) or (0, None) if no dates were found.
    """
    today = today or date.today()
    now = today.year * 12 + today.month - 1
    work = {"experience"} if profile.has_section("experience") else {"general", "experience"}

    spans, first_line = [], None
    for line in profile.lines:
        if line.section not in work:
            continue
        for m in DATE_RANGE.finditer(line.text):
            start = _month_index(m, "s")
            end = now if m.group("present") else _month_index(m, "e")
            if start is None or end is None or end < start or start > now:
                continue
            spans.append((start, min(end, now)))
            first_line = first_line or line.text

    total, current_end = 0, -1
    for start, end in sorted(spans):
        start = max(start, current_end)
        if end > start:
            total += end - start
        current_end = max(current_end, end)
    return round(total / 12, 1), first_line
