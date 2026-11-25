"""One test group per rule: just below, at and just above every limit. No data files and no API key needed."""
from datetime import date, timedelta

import pytest

import config as C
from agent import rules as R

D = date(2026, 3, 1)


def days(n, base=D):
    return base + timedelta(days=n)


# ---- config: every rule has a document and page reference -----------------------------------------
def test_every_rule_has_a_clause_with_document_and_page():
    for rule in ("R1", "R2", "R3", "R4", "R5", "R6", "R12"):
        text = C.CLAUSES[rule]
        assert text[:2] in ("02", "03") and " p" in text and " s" in text, rule


# ---- R1 claim windows (02 p3 s5.2) -----------------------------------------------------------------
@pytest.mark.parametrize("d,expected", [(-91, R.FLAG), (-90, R.PASS), (-1, R.PASS), (0, R.PASS), (1, R.FLAG)])
def test_r1_near_expiry(d, expected):
    assert R.r1_window(C.NEAR_EXPIRY, days(d), D).status == expected


@pytest.mark.parametrize("d,expected", [(-1, R.FLAG), (0, R.PASS), (90, R.PASS), (91, R.FLAG)])
def test_r1_expired(d, expected):
    assert R.r1_window(C.EXPIRED, days(d), D).status == expected


@pytest.mark.parametrize("d,expected", [(-1, R.FLAG), (0, R.PASS), (7, R.PASS), (8, R.FLAG)])
@pytest.mark.parametrize("kind", [C.BREAKAGE, C.SHORT_SUPPLY])
def test_r1_breakage_and_short_supply(kind, d, expected):
    assert R.r1_window(kind, days(d), D, invoice_date=D).status == expected


def test_r1_breakage_without_invoice_date_is_not_tested_and_unknown_type_needs_a_person():
    assert R.r1_window(C.BREAKAGE, D, D).status == R.NOT_TESTABLE
    assert R.r1_window("Damaged", D, D).status == R.NEEDS_PERSON


def test_r1_flag_points_to_the_whole_claim_value():
    c = R.r1_window(C.EXPIRED, days(91), D)
    assert c.amount_basis == "claim" and c.detail["days from expiry"] == 91


# ---- R2 invoice reference or approval (02 p3 s5.3-5.4) ---------------------------------------------
def test_r2_reference_present_passes():
    assert R.r2_invoice_reference("INV/N02/2506/039882", None, invoice_found=True).status == R.PASS


def test_r2_reference_not_in_sales_file_needs_a_person():
    assert R.r2_invoice_reference("INV/X/0000/000000", None, invoice_found=False).status == R.NEEDS_PERSON


@pytest.mark.parametrize("blank", [None, "", "  ", float("nan")])
def test_r2_blank_reference_without_approval_is_flagged(blank):
    c = R.r2_invoice_reference(blank, "Party says invoice misplaced")
    assert c.status == R.FLAG and c.amount_basis == "claim"


def test_r2_blank_reference_with_recorded_approval_passes():
    assert R.r2_invoice_reference(None, "Approved in writing by Area Manager").status == R.PASS


# ---- R3 quantity within packs supplied (02 p3 s5.5) ------------------------------------------------
@pytest.mark.parametrize("qty,expected,excess", [(99, R.PASS, 0), (100, R.PASS, 0), (101, R.FLAG, 1)])
def test_r3_at_and_above_the_supplied_quantity(qty, expected, excess):
    c = R.r3_quantity(qty, supplied=100, claimed_before=0, pts=10.0)
    assert c.status == expected and c.detail["excess_packs"] == excess


def test_r3_counts_earlier_claims_and_prices_only_the_excess():
    c = R.r3_quantity(50, supplied=100, claimed_before=60, pts=12.5)
    assert c.status == R.FLAG and c.detail["excess_packs"] == 10 and c.amount_inr == 125.0 and c.amount_basis == "excess"


def test_r3_excess_never_exceeds_this_claim():
    assert R.r3_quantity(5, supplied=100, claimed_before=200, pts=1.0).detail["excess_packs"] == 5


def test_r3_no_supply_record_is_not_tested():
    assert R.r3_quantity(10, supplied=None, claimed_before=0, pts=1.0).status == R.NOT_TESTABLE


# ---- R4 earlier claim on the same stockist and batch (02 p4 s5.6; 03 p3 s2.6) ----------------------
def test_r4_no_earlier_claim_passes():
    assert R.r4_repeat(10, []).status == R.PASS


def test_r4_same_quantity_earlier_claim_is_a_probable_duplicate():
    for status in ("Credited", "Pending"):
        assert R.r4_repeat(10, [(10, status)]).status == R.FLAG


def test_r4_rejected_duplicate_or_different_quantity_is_not_flagged():
    assert R.r4_repeat(10, [(10, "Rejected")]).status == R.PASS
    c = R.r4_repeat(10, [(9, "Credited")])
    assert c.status == R.PASS and c.detail["earlier_claims"] == 1


# ---- R5 valuation (02 p4 s5.7) ---------------------------------------------------------------------
def test_r5_value_equals_quantity_times_pts():
    assert R.r5_value(38, 103.6, 3936.8).status == R.PASS
    assert R.r5_value(38, 103.6, 3936.795).status == R.PASS       # 0.005 off, inside the 0.01 tolerance
    assert R.r5_value(38, 103.6, 3936.78).status == R.FLAG        # 0.02 off
    assert R.r5_value(38, 103.6, 3937.0).status == R.FLAG


def test_r5_blank_recorded_value_is_derived_not_invented():
    c = R.r5_value(10, 71.4, None)
    assert c.status == R.PASS and c.detail["expected_inr"] == 714.0 and c.detail["recorded_inr"] is None


# ---- R6 credit note within 30 days (02 p4 s5.6) ----------------------------------------------------
@pytest.mark.parametrize("n,expected", [(29, R.PASS), (30, R.PASS), (31, R.FLAG)])
def test_r6_issued_credit_note(n, expected):
    assert R.r6_clock(D, credit_note_date=days(n)).status == expected


def test_r6_pending_claim_shows_the_due_date_and_flags_when_overdue():
    assert R.r6_clock(D).detail["credit_note_due"] == "2026-03-31"
    assert R.r6_clock(D, asof=days(30)).status == R.PASS
    assert R.r6_clock(D, asof=days(31)).status == R.FLAG


# ---- R12 claim number (03 p3 s2.6) -----------------------------------------------------------------
def test_r12_matching_number_passes_and_mismatch_needs_a_person():
    assert R.r12_claim_number("CLM-2603-04177", date(2026, 3, 18)).status == R.PASS
    c = R.r12_claim_number("CLM-2602-04177", date(2026, 3, 18))
    assert c.status == R.NEEDS_PERSON and "which date is true" in c.summary


@pytest.mark.parametrize("bad", ["CLM-2603-4177", "clm-2603-04177", "", None, "CLM-2613-04177x"])
def test_r12_bad_format_needs_a_person(bad):
    assert R.r12_claim_number(bad, date(2026, 3, 18)).status == R.NEEDS_PERSON


# ---- decide: routing and rupees at issue -----------------------------------------------------------
def ok(rule):
    return R.Check(rule, R.PASS, "ok")


def test_all_clear_goes_to_credit_for_review():
    out = R.decide([ok(r) for r in ("R1", "R2", "R3", "R4", "R5", "R6", "R12")], 1000)
    assert out["route"] == C.CREDIT_FOR_REVIEW and out["amount_at_issue_inr"] == 0


def test_a_blocking_flag_holds_and_the_amount_is_the_largest_not_the_sum():
    flagged = [R.Check("R1", R.FLAG, "late", amount_basis="claim"),
               R.Check("R3", R.FLAG, "excess", amount_inr=300.0, amount_basis="excess"), ok("R2"), ok("R4")]
    out = R.decide(flagged, claim_value_inr=1000.0)
    assert out["route"] == C.HOLD and out["amount_at_issue_inr"] == 1000.0 and len(out["reasons"]) == 2
    only_excess = R.decide([R.Check("R3", R.FLAG, "excess", amount_inr=300.0, amount_basis="excess"), ok("R1")], 1000.0)
    assert only_excess["amount_at_issue_inr"] == 300.0


def test_needs_person_beats_hold_and_untestable_blocking_rules_need_a_person():
    out = R.decide([R.Check("R12", R.NEEDS_PERSON, "dates disagree"), R.Check("R1", R.FLAG, "late", amount_basis="claim")], 500)
    assert out["route"] == C.NEEDS_PERSON
    assert R.decide([R.Check("R3", R.NOT_TESTABLE, "no supply record"), ok("R1")], 500)["route"] == C.NEEDS_PERSON


def test_late_credit_note_informs_but_does_not_hold():
    out = R.decide([ok("R1"), ok("R2"), ok("R3"), ok("R4"), R.Check("R6", R.FLAG, "45 days")], 500)
    assert out["route"] == C.CREDIT_FOR_REVIEW and out["informational"] == ["R6: 45 days"]
