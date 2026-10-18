"""Skills dictionary (data/skills.json) and keyword search."""

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .text import stem

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "skills.json"

# A keyword must not touch other word characters. "+#" keeps C++/C# whole, "." keeps
# "Node.js" from matching inside other tokens. Case-sensitive (common-English) terms also
# refuse "-" and "&" neighbours so "Go-to-market" or "R&D" don't count.
_BOUNDARY_BEFORE = r"(?<![\w+#.])"
_BOUNDARY_AFTER = r"(?![\w+#]|\.\w)"
_STRICT_BEFORE = r"(?<![\w+#.&-])"
_STRICT_AFTER = r"(?![\w+#&-]|\.\w)"


@dataclass(frozen=True)
class Skill:
    name: str
    category: str
    patterns: tuple[re.Pattern, ...]
    related: frozenset[str]  # lowercase aliases that are related terms, not true synonyms

    def is_related(self, surface: str) -> bool:
        return surface.lower() in self.related


@dataclass(frozen=True)
class Hit:
    skill: Skill
    surface: str  # the text as it appeared
    start: int
    end: int


def _parse_term(term: str) -> tuple[str, bool, bool]:
    """'~=CI' -> ('CI', related=True, exact=True)."""
    related = term.startswith("~")
    term = term.lstrip("~")
    exact = term.startswith("=")
    return term.lstrip("="), related, exact


def compile_term(term: str, exact: bool) -> re.Pattern:
    """Exact terms are case-sensitive with strict boundaries; others are case-insensitive."""
    if exact:
        return re.compile(_STRICT_BEFORE + re.escape(term) + _STRICT_AFTER)
    escaped = re.escape(term).replace(r"\ ", r"[\s-]+")
    return re.compile(_BOUNDARY_BEFORE + escaped + _BOUNDARY_AFTER, re.IGNORECASE)


def _entries() -> list[tuple[str, str, list[str]]]:
    data = json.loads(DATA_FILE.read_text())
    return [
        (category, name, aliases)
        for category, entries in data.items() if not category.startswith("_")
        for name, aliases in entries.items()
    ]


@lru_cache(maxsize=1)
def load_skills() -> tuple[Skill, ...]:
    skills = []
    for category, name, aliases in _entries():
        parsed = [_parse_term(t) for t in dict.fromkeys([name, *aliases])]
        # Longer terms first so "Google Cloud Platform" wins over "Google Cloud".
        parsed.sort(key=lambda p: -len(p[0]))
        skills.append(Skill(
            name=_parse_term(name)[0],
            category=category,
            patterns=tuple(compile_term(t, exact) for t, _, exact in parsed),
            related=frozenset(t.lower() for t, rel, _ in parsed if rel),
        ))
    return tuple(skills)


@lru_cache(maxsize=1)
def known_terms_lower() -> frozenset[str]:
    return frozenset(
        _parse_term(t)[0].lower()
        for _, name, aliases in _entries() for t in [name, *aliases]
    )


def find_skills(text: str) -> list[Hit]:
    """All dictionary hits in text. Within one skill, overlapping alias hits are merged
    (the longest alias wins, since patterns are sorted longest-first)."""
    hits: list[Hit] = []
    for skill in load_skills():
        taken: list[tuple[int, int]] = []
        for pattern in skill.patterns:
            for m in pattern.finditer(text):
                if any(m.start() < end and start < m.end() for start, end in taken):
                    continue
                taken.append((m.start(), m.end()))
                hits.append(Hit(skill, m.group(0), m.start(), m.end()))
    hits.sort(key=lambda h: h.start)
    return hits


def same_wording(a: str, b: str) -> bool:
    """True for trivial variants: "React"/"React.js", "API"/"APIs", "mentor"/"mentoring",
    "REST"/"REST APIs". Different names ("k8s"/"Kubernetes") are not the same wording."""
    def words(s: str) -> set[str]:
        return {stem(w) for w in re.findall(r"[a-z0-9+#]+", s.lower())}
    wa, wb = words(a), words(b)
    return bool(wa and wb) and (wa <= wb or wb <= wa)
