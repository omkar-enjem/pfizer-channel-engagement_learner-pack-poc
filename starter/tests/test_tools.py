"""Tests that run without an API key. Add one test for every rule you put in code."""
from agent.tools import batch_record


def test_known_batch_is_found():
    rec = batch_record("K2300101")
    assert rec["found"] is True
    assert rec["sku_code"] == "PFL1001"


def test_unknown_batch_is_reported_not_invented():
    rec = batch_record("ZZ999")
    assert rec["found"] is False


def test_batch_lookup_ignores_case_and_spaces():
    assert batch_record("  k2300101 ")["found"] is True
