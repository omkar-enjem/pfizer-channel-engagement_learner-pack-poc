"""Needs langgraph (pip install -r requirements.txt). Checks the graph gives the same answers as the plain-Python loop."""
import json

import pytest

pytest.importorskip("langgraph")

from agent import graph as G
from agent import pipeline as P


def model(system, user):
    if "read one email" in system:
        return json.dumps({"lines": [{"intent": "expiry_claim", "batch_no": "M2400719", "qty": 693, "unit": "strips", "invoice_ref": "INV/S01/2506/041964"}]})
    return "Short note."


def strip(r):
    return {k: v for k, v in r.items() if k != "model_calls"}


@pytest.mark.parametrize("text", ["CLM-2608-02345", "CLM-2609-99999", "EML-014", "EML-006"])
def test_graph_matches_plain_loop(text):
    g = G.build(model)
    assert [strip(x) for x in G.run_all(text, graph=g)] == [strip(x) for x in P.run_sequential({"input": text}, model)]


def test_all_register_claims_run_seven_checks_in_the_graph():
    r = G.run_all("CLM-2608-02345", model_call=model)[0]
    assert [c["rule"] for c in r["checks"]] == ["R1", "R2", "R3", "R4", "R5", "R6", "R12"]


def test_graph_draws_every_node():
    text = G.draw()
    for node in ["read_email", "fetch", "route", "explain"] + [f"check_{r}" for r in ("R1", "R2", "R3", "R4", "R5", "R6", "R12")]:
        assert node in text
