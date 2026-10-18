"""Small text utilities shared by the built-in engine."""

import re
from dataclasses import dataclass

BULLET_RE = re.compile(r"^\s*(?:[-*•·▪◦‣●○■□➢►✓>]+|\d{1,2}[.)])\s+")

STOPWORDS = set(
    """a an and are as at be been being by for from has have in into is it its of on or our
    that the their them they this to was were will with within you your we us who what when
    where which while all any both each more most other some such than too very can could
    should would may might must also etc using use used across including include includes
    new strong excellent good great ability able work working role team teams company per
    via well based like make makes help helps ensure ensuring within over about up out""".split()
)


@dataclass
class Line:
    text: str      # the line as written, minus any leading bullet marker (verbatim substring)
    section: str   # section the line belongs to
    is_bullet: bool


def clean(line: str) -> str:
    return BULLET_RE.sub("", line).strip()


def stem(word: str) -> str:
    """Crude suffix stripping so "managed", "managing" and "manages" compare equal."""
    for suffix in ("ations", "ation", "ments", "ment", "ings", "ing", "ies", "ed", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)]
    return word


def tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z][a-z0-9+#.]*[a-z0-9+#]|[a-z]", text.lower())
    return {stem(w) for w in words if w not in STOPWORDS and len(w) > 1}


def _header_key(line: str) -> str:
    line = line.lower().replace("’", "'").replace("-", " ")
    return re.sub(r"[^a-z&' ]", "", line).strip()


def split_sections(
    text: str,
    headers: dict[str, list[str]],
    default: str,
    strict: bool = False,
    is_header_candidate=lambda line: True,
) -> list[Line]:
    """Split text into lines tagged with the section they appear under.

    `headers` maps a section name to phrases that identify its heading. A line counts as a
    heading when it is short, doesn't read like a sentence, and contains one of the
    phrases. "Skills: Python, SQL" style lines switch section and keep the rest as content.
    """
    section = default
    out: list[Line] = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped:
            continue

        is_bullet = bool(BULLET_RE.match(raw))
        head, sep, rest = stripped.partition(":")
        candidate = head if sep else stripped
        found = (
            _match_header(candidate, headers, strict)
            if not is_bullet and is_header_candidate(candidate)
            else None
        )
        if found and (not sep or len(head.split()) <= 4):
            section = found
            if sep and rest.strip():
                out.append(Line(rest.strip(), section, False))
            continue

        out.append(Line(clean(stripped), section, is_bullet))
    return out


HEADER_QUALIFIERS = {
    "professional", "work", "relevant", "technical", "core", "key", "additional", "selected",
    "my", "other", "and", "&", "personal", "academic", "career", "areas", "of",
}


def _match_header(candidate: str, headers: dict[str, list[str]], strict: bool) -> str | None:
    if len(candidate) > 60 or len(candidate.split()) > 7 or candidate.rstrip().endswith("."):
        return None
    if "," in candidate:
        return None
    key = _header_key(candidate)
    if strict:
        # Resume headings are terse ("Work Experience", "SKILLS"): after dropping qualifier
        # words, every remaining word must belong to a heading phrase.
        words = [w for w in key.split() if w not in HEADER_QUALIFIERS]
        if not words:
            return None
        for section, phrases in headers.items():
            vocab = {w for p in phrases for w in p.split()}
            if all(w in vocab for w in words):
                return section
        return None
    for section, phrases in headers.items():
        if any(p in key for p in phrases):
            return section
    return None
