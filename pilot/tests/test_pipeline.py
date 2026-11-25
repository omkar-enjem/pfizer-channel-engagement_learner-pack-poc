"""Workflow tests with a fake model: no network, no LangGraph needed. Each rule's own tests are in test_rules.py."""
import json

import pytest

from agent import pipeline as P

CLAIM_JSON = lambda **k: json.dumps({"lines": [{"intent": "expiry_claim", "product": None, "batch_no": None, "expiry_text": None, "qty": None,
                                                "unit": "strips", "strips_per_box": None, "invoice_ref": None, "claim_no": None, **k}]})


def fake(read=None, explain="Credit for review."):
    calls = []

    def call(system, user):
        calls.append('read' if 'read one email' in system else 'explain')
        if "read one email" in system:
            if isinstance(read, Exception):
                raise read
            return read
        if isinstance(explain, Exception):
            raise explain
        return explain
    call.calls = calls
    return call


def one(text, model, **kw):
    out = P.run_sequential({"input": text, **kw}, model)
    assert len(out) == 1
    return out[0]


def test_claim_number_makes_no_read_call_and_one_explain_call():
    m = fake()
    r = one("CLM-2608-02345", m)
    assert r["recommendation"] in ("credit_for_review", "hold", "needs_person")
    assert m.calls == ["explain"] and r["model_calls"] == 1


def test_unknown_claim_needs_a_person():
    r = one("CLM-2609-99999", fake())
    assert r["recommendation"] == "needs_person" and "not in the claims file" in r["reasons"][0]


def test_model_failure_in_explain_uses_template_and_keeps_decision():
    a = one("CLM-2608-02345", fake())
    b = one("CLM-2608-02345", fake(explain=TimeoutError("slow")))
    assert b["recommendation"] == a["recommendation"] and b["explanation_source"] == "template"


def test_explanation_with_invented_number_is_replaced():
    r = one("CLM-2608-02345", fake(explain="Credit Rs 9,87,654 immediately."))
    assert r["explanation_source"] == "template" and "987654" not in r["explanation"]


def test_explanation_with_only_known_numbers_is_kept():
    ok = one("CLM-2608-02345", fake(explain="Fine."))
    assert ok["explanation_source"] == "model"


def test_email_read_failure_retries_once_then_needs_person():
    m = fake(read=ValueError("down"))
    r = one("EML-022", m)
    assert r["recommendation"] == "needs_person" and r["model_calls"] == 2
    assert m.calls == ["read", "read"]


def test_email_bad_json_then_good_json_on_retry():
    seq = iter(["not json", CLAIM_JSON(batch_no="D2500228", qty=241, invoice_ref="INV/N02/2506/039882")])
    m = fake()
    base = m

    def call(system, user):
        return next(seq) if "read one email" in system else base(system, user)
    r = one("EML-022", call)
    assert r["recommendation"] in ("credit_for_review", "hold", "needs_person")
    assert r["model_calls"] == 2


def test_email_blank_batch_needs_a_person():
    r = one("EML-006", fake(read=CLAIM_JSON(qty=168)))
    assert r["recommendation"] == "needs_person" and "batch" in r["reasons"][0].lower()


def test_email_unknown_sender_needs_a_person():
    r = one("EML-018", fake(read=CLAIM_JSON(batch_no="K2300101", qty=10)))
    assert r["recommendation"] == "needs_person" and "stockist" in r["reasons"][0].lower()


def test_email_boxes_converted_in_code_and_runs_checks():
    r = one("EML-008", fake(read=CLAIM_JSON(batch_no="L2420268", qty=43, unit="boxes", strips_per_box=10, invoice_ref="INV/N02/2505/036911")))
    assert r["claim"]["qty_claimed"] == 430
    assert [c["rule"] for c in r["checks"]] == ["R1", "R2", "R3", "R4", "R5"]


def test_boxes_without_strips_per_box_needs_a_person():
    r = one("EML-008", fake(read=CLAIM_JSON(batch_no="L2420268", qty=43, unit="boxes")))
    assert r["recommendation"] == "needs_person" and "strips per box" in r["reasons"][0]


def test_instruction_in_email_is_ignored_and_noted():
    r = one("EML-017", fake(read=CLAIM_JSON(batch_no="K2430146", qty=705, invoice_ref="INV/S01/2502/029631")))
    assert any("instructions" in n for n in r["notes"])
    assert r["recommendation"] != "credit_for_review" or all(c["status"] != "flag" for c in r["checks"])


def test_non_claim_email_needs_a_person():
    r = one("EML-029", fake(read=json.dumps({"lines": [{"intent": "other"}]})))
    assert r["recommendation"] == "needs_person"


def test_status_query_runs_the_claim_checks():
    r = one("EML-025", fake(read=json.dumps({"lines": [{"intent": "status_query", "claim_no": "CLM-2608-02345"}]})))
    assert r["claim"]["claim_no"] == "CLM-2608-02345"


def test_three_line_email_gives_three_answers():
    three = json.dumps({"lines": [{"intent": "expiry_claim", "batch_no": b, "qty": q, "unit": "strips", "invoice_ref": i}
                                  for b, q, i in (("J2420408", 142, "INV/E01/2504/035116"), ("K2410413", 134, "INV/E01/2504/034822"), ("J2400578", 42, "INV/E01/2504/035037"))]})
    out = P.run_sequential({"input": "EML-002"}, fake(read=three))
    assert len(out) == 3 and [o["case_number"] for o in out] == [1, 2, 3]


def test_hyphen_invoice_is_normalised():
    claim, why = P.build_email_claim({"batch_no": "E2510535", "qty": 68, "unit": "strips", "invoice_ref": "INV-S02-2510-053444"}, "STK0126", "2026-10-14")
    assert claim["original_invoice_ref"] == "INV/S02/2510/053444"


def test_input_kinds():
    assert P.classify_input(" clm-2608-02345 ") == "claim_no" and P.classify_input("EML-001") == "email_id" and P.classify_input("hello") == "email_text"


def test_number_guard():
    assert P.explanation_ok("Excess 12 packs", {"x": 12}) and not P.explanation_ok("Excess 13 packs", {"x": 12})


def test_repeat_line_inside_one_email_is_a_probable_duplicate():
    line = {"intent": "expiry_claim", "batch_no": "L2430266", "qty": 61, "unit": "strips", "invoice_ref": "INV/S02/2504/036190"}
    out = P.run_sequential({"input": "EML-013"}, fake(read=json.dumps({"lines": [line, line]})))
    assert len(out) == 2
    assert not any(c["status"] == "flag" and c["rule"] == "R4" for c in out[0]["checks"])
    assert any(c["status"] == "flag" and c["rule"] == "R4" for c in out[1]["checks"])


def test_numbers_spelled_out_are_rejected():
    assert not P.explanation_ok("Sixty-one strips claimed", {"x": 61})
    assert not P.explanation_ok("two thousand supplied", {"x": 2000})
    r = one("CLM-2608-02345", fake(explain="Credit for review. Four hundred forty-seven strips claimed."))
    assert r["explanation_source"] == "template"


def test_markdown_marks_are_removed():
    r = one("CLM-2608-02345", fake(explain="**Credit for review**: fine."))
    assert "*" not in r["explanation"] and r["explanation_source"] == "model"
