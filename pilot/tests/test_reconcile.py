"""The pilot's rules, run over all 4,503 claims, must reproduce the counts validated in notebooks/step4_rules.ipynb.

If one of these fails, either the code or the analysis is wrong: find out which before going on.
"""
import pandas as pd
import pytest

import config as C
from agent import rules as R
from agent.check import check_claim
from agent.data import load


@pytest.fixture(scope="module")
def results():
    claims = load("expiry_claims")
    out = {n: check_claim(n) for n in claims.claim_no}
    return claims, out


def by_rule(results, rule):
    claims, out = results
    return {n: next(c for c in r["checks"] if c["rule"] == rule) for n, r in out.items()}, claims.set_index("claim_no").status


def test_every_claim_is_found_and_has_seven_checks(results):
    claims, out = results
    assert len(out) == 4503 and all(r["found"] and len(r["checks"]) == 7 for r in out.values())


def test_r1_matches_notebook(results):                       # 4,428 testable, 519 breaches
    c, _ = by_rule(results, "R1")
    assert sum(x["status"] != R.NOT_TESTABLE for x in c.values()) == 4428
    assert sum(x["status"] == R.FLAG for x in c.values()) == 519


def test_r2_matches_notebook(results):                       # 879 blank references; 861 on Credited or Pending claims with no approval
    c, st = by_rule(results, "R2")
    flagged = [n for n, x in c.items() if x["status"] == R.FLAG]
    assert len(flagged) == 879
    assert sum(1 for n in flagged if st[n] in ("Credited", "Pending")) == 861      # the notebook leaves out the 18 Rejected
    # 768 older claims quote invoices that are not in the sales file (numbers like INV/W01/2302/..., before the extract starts in Apr 2024)
    claims, _ = results
    dates = claims.set_index("claim_no").claim_date
    unknown = [n for n, x in c.items() if x["status"] == R.NEEDS_PERSON]
    assert len(unknown) == 768
    assert dates[unknown].min() == pd.Timestamp("2024-07-01") and dates[unknown].max() == pd.Timestamp("2025-03-27")
    assert (dates >= "2025-10-01")[unknown].sum() == 0                              # none in the 12-month window


def test_r3_matches_notebook(results):                       # 3,532 testable, 44 breaches among claims not rejected
    c, st = by_rule(results, "R3")
    assert sum(x["status"] != R.NOT_TESTABLE for x in c.values()) == 3532
    assert sum(1 for n, x in c.items() if x["status"] == R.FLAG and st[n] != "Rejected") == 44


def test_r4_matches_notebook(results):                       # 526 repeats, 98 probable duplicates
    c, _ = by_rule(results, "R4")
    assert sum(x["detail"]["earlier_claims"] > 0 for x in c.values()) == 526
    assert sum(x["status"] == R.FLAG for x in c.values()) == 98


def test_r5_matches_notebook(results):                       # every recorded value equals quantity x PTS
    c, _ = by_rule(results, "R5")
    assert all(x["status"] == R.PASS for x in c.values())


def test_r6_matches_notebook(results):                       # 3,115 of 4,112 credit notes late; 129 of 360 pending over 30 days
    c, st = by_rule(results, "R6")
    assert sum(1 for n, x in c.items() if st[n] == "Credited" and x["status"] == R.FLAG) == 3115
    assert sum(1 for n, x in c.items() if st[n] == "Pending" and x["status"] == R.FLAG) == 129


def test_r12_matches_notebook(results):                      # 84 claims whose number month differs from the claim date
    c, _ = by_rule(results, "R12")
    assert sum(x["status"] == R.NEEDS_PERSON for x in c.values()) == 84


def test_routes_are_consistent_with_the_checks(results):
    _, out = results
    for r in out.values():
        st = {c["rule"]: c["status"] for c in r["checks"]}
        route = r["decision"]["route"]
        if route == C.CREDIT_FOR_REVIEW:
            assert all(st[x] == R.PASS for x in C.BLOCKING_RULES) and R.NEEDS_PERSON not in st.values()
        if route == C.HOLD:
            assert R.FLAG in [st[x] for x in C.BLOCKING_RULES] and R.NEEDS_PERSON not in st.values() and r["decision"]["amount_at_issue_inr"] > 0


def test_every_number_on_screen_has_a_source(results):
    _, out = results
    for r in out.values():
        for e in r["evidence"]:
            assert e["file"].endswith(".csv") and e["rows"] and all(isinstance(x, int) for x in e["rows"])
        assert r["evidence"][0]["file"] == "expiry_claims.csv"


def test_unknown_claim_is_not_found_and_goes_to_a_person():
    r = check_claim("CLM-0000-00000")
    assert r["found"] is False and r["decision"]["route"] == C.NEEDS_PERSON and r["evidence"] == []
