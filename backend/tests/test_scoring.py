from app.models import Requirement, RewrittenBullet
from app.scoring import compute_score, normalize, verify_bullets, verify_requirements

RESUME = """Jane Doe
• Built REST APIs in Python with FastAPI serving 2M requests/day
- Led migration of “legacy” services to AWS
"""


def req(term, status, importance="required", evidence=""):
    return Requirement(
        term=term, category="tool", importance=importance,
        status=status, resume_evidence=evidence, note="",
    )


def test_normalize_handles_bullets_quotes_and_whitespace():
    assert normalize("•  Led   migration of “legacy” services.") == 'led migration of "legacy" services'


def test_markdown_bold_resume_still_verifies():
    resume = "- Built **REST APIs** in __Python__ with `FastAPI`"
    [r] = verify_requirements([req("Python", "matched", evidence="REST APIs in Python with FastAPI")], resume)
    assert r.status == "matched"


def test_unicode_bold_resume_still_verifies():
    resume = "• Built REST APIs in 𝐏𝐲𝐭𝐡𝐨𝐧"
    [r] = verify_requirements([req("Python", "matched", evidence="REST APIs in Python")], resume)
    assert r.status == "matched"
    bullets = [RewrittenBullet(original="Built REST APIs in Python", improved="x", keywords_used=[])]
    assert len(verify_bullets(bullets, resume)) == 1


def test_matched_with_verbatim_evidence_stays_matched():
    [r] = verify_requirements([req("FastAPI", "matched", evidence="Python with FastAPI")], RESUME)
    assert r.status == "matched"
    assert r.resume_evidence == "Python with FastAPI"


def test_matched_with_fabricated_evidence_is_downgraded():
    [r] = verify_requirements([req("Kubernetes", "matched", evidence="Managed Kubernetes clusters")], RESUME)
    assert r.status == "partial"
    assert r.resume_evidence == ""


def test_score_weights_required_over_preferred():
    breakdown = compute_score([
        req("A", "matched"),                         # 3 / 3
        req("B", "partial"),                         # 1.5 / 3
        req("C", "missing", importance="preferred"), # 0 / 1
    ])
    assert breakdown.score == round(100 * 4.5 / 7)
    assert (breakdown.matched, breakdown.partial, breakdown.missing) == (1, 1, 1)
    assert "guarantee" in breakdown.disclaimer


def test_score_is_zero_without_requirements():
    assert compute_score([]).score == 0


def test_bullets_with_invented_originals_are_dropped():
    bullets = [
        RewrittenBullet(original="Led migration of \"legacy\" services to AWS", improved="x", keywords_used=[]),
        RewrittenBullet(original="Won the Turing Award", improved="y", keywords_used=[]),
    ]
    assert [b.improved for b in verify_bullets(bullets, RESUME)] == ["x"]
