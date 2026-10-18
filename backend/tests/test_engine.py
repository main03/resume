from datetime import date

from app import engine
from app.engine.resume import experience_years, parse_resume

JOB = """Backend Engineer

About Us
Our stack includes Elixir.

Requirements
- 3+ years of software engineering experience
- Python, Kubernetes and CI/CD
- Bachelor's degree in Computer Science

Nice to have: Terraform
"""

RESUME = """SUMMARY
Backend engineer.

EXPERIENCE
Engineer, Acme — Jan 2020 – Dec 2023
• Built REST APIs in Python
• Deployed services to k8s and maintained the CI pipeline

SKILLS
Terraform

EDUCATION
B.S. Computer Science
"""


def by_term(analysis):
    return {r.term: r for r in analysis.requirements}


def test_builtin_engine_end_to_end():
    analysis = engine.analyze(RESUME, JOB)
    reqs = by_term(analysis)

    assert analysis.role_title == "Backend Engineer"
    assert "Elixir" not in reqs                              # "About Us" is ignored
    assert reqs["Python"].status == "matched"
    assert reqs["Kubernetes"].status == "partial"            # synonym: k8s
    assert reqs["CI/CD"].status == "partial"                 # related term: CI
    assert reqs["Terraform"].importance == "preferred"
    assert reqs["Terraform"].status == "partial"             # only in skills list
    assert reqs["Bachelor's degree"].status == "matched"
    assert reqs["3+ years of experience"].status == "matched"

    # Synonyms are swapped in; related terms (CI -> CI/CD) never are.
    [rewrite] = analysis.rewritten_bullets
    assert rewrite.improved == "Deployed services to Kubernetes (k8s) and maintained the CI pipeline"


def test_experience_years_merges_overlaps():
    profile = parse_resume("EXPERIENCE\nA — Jan 2018 – Dec 2020\nB — Jan 2020 – Present\n")
    years, _ = experience_years(profile, today=date(2024, 1, 1))
    assert years == 6.0
