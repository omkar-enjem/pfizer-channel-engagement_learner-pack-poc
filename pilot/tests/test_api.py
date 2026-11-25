"""The API with a fake model: no key, no cost. Needs fastapi and httpx (pip install -r requirements.txt)."""
import json

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("langgraph")
from fastapi.testclient import TestClient

import app as web
from agent import graph as G


def fake(system, user):
    if "read one email" in system:
        return json.dumps({"lines": [{"intent": "expiry_claim", "batch_no": "M2400719", "qty": 693, "unit": "strips", "invoice_ref": "INV/S01/2506/041964"}]})
    return "Short note."


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(web, "_GRAPH", G.build(fake))
    return TestClient(web.app)


def test_health(client):
    j = client.get("/api/health").json()
    assert j["ok"] is True and j["claims"] == 4503


def test_check_claim_number(client):
    r = client.post("/api/check", json={"input": "CLM-2608-02345"})
    assert r.status_code == 200
    res = r.json()["results"][0]
    assert res["claim"]["claim_no"] == "CLM-2608-02345" and len(res["checks"]) == 7 and res["evidence"]


def test_check_email_id(client):
    res = client.post("/api/check", json={"input": "EML-014"}).json()["results"][0]
    assert res["recommendation"] == "hold" and any("R3" in x for x in res["reasons"])


def test_unknown_claim_is_needs_a_person_not_an_error(client):
    r = client.post("/api/check", json={"input": "CLM-2609-99999"})
    assert r.status_code == 200 and r.json()["results"][0]["recommendation"] == "needs_person"


def test_empty_input_is_400(client):
    assert client.post("/api/check", json={"input": " "}).status_code == 400


def test_emails_endpoint(client):
    assert len(client.get("/api/emails").json()) == 30
