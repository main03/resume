from fastapi.testclient import TestClient

from app import main

client = TestClient(main.app)

RESUME = (
    "EXPERIENCE\nEngineer, Acme — Jan 2020 – Present\n"
    "- Built REST APIs in Python with FastAPI for a payments platform.\n"
    "- Deployed services to k8s.\n"
)
JOB = (
    "Backend Engineer\n\nRequirements\n"
    "- Python and FastAPI\n- Kubernetes\n- Experience with GraphQL is a plus\n"
)


def test_analyze_returns_scored_report():
    res = client.post("/api/analyze", json={"resume": RESUME, "job_description": JOB})
    assert res.status_code == 200
    body = res.json()
    statuses = {r["term"]: r["status"] for r in body["requirements"]}
    assert statuses["Python"] == "matched"
    assert statuses["Kubernetes"] == "partial"
    assert statuses["GraphQL"] == "missing"
    assert 0 < body["score"]["score"] < 100
    assert "guarantee" in body["score"]["disclaimer"]


def test_short_input_is_rejected():
    res = client.post("/api/analyze", json={"resume": "too short", "job_description": JOB})
    assert res.status_code == 422
