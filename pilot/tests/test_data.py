"""Tests for agent/data.py. They read the committed data/ folder (no API key needed)."""
import pandas as pd
import pytest

from agent import data
from agent.data import DataError, fy_quarter, load, load_all


def test_every_table_loads_with_expected_rows():
    for name, df in load_all().items():
        assert len(df) == data.EXPECTED_ROWS[name]


def test_dates_are_real_dates_and_flags_are_booleans():
    for name, cols in data.DATE_COLS.items():
        for c in cols:
            assert pd.api.types.is_datetime64_any_dtype(load(name)[c]), f"{name}.{c}"
    for name, cols in data.FLAG_COLS.items():
        for c in cols:
            assert load(name)[c].dtype == bool, f"{name}.{c}"


def test_blanks_are_kept_blank_and_no_scheme_label_is_set():
    ps, ec, st = load("primary_sales"), load("expiry_claims"), load("stockist_master")
    assert not ps.scheme_code.isin(["", "NA", "-"]).any()
    assert (ps.scheme_code == "NO_SCHEME").sum() == 80453
    assert ec.claim_value_inr.isna().sum() == 135          # never filled
    assert st.appointed_on.isna().sum() == 150             # documented: not migrated (01 p3 s5.3)
    assert (ps.batch_no.isna() == ps.is_cancelled_line).all()   # blank batch = line not supplied (01 p3 s5.4)


def test_derived_claim_value_is_apart_from_recorded_value():
    ec, sku = load("expiry_claims"), load("sku_master").set_index("sku_code").pts_inr
    assert ec.claim_value_derived_inr.notna().all()
    assert ec.claim_value_was_derived.sum() == 135
    rec = ec[~ec.claim_value_was_derived]
    assert (rec.claim_value_derived_inr == rec.claim_value_inr).all()
    assert ((ec.qty_claimed * ec.sku_code.map(sku) - ec.claim_value_derived_inr).abs() < 0.01).all()


def test_links_hold():
    ps, ec = load("primary_sales"), load("expiry_claims")
    sku, stk, bat = (set(load(n)[c]) for n, c in [("sku_master", "sku_code"), ("stockist_master", "stockist_code"), ("batch_master", "batch_no")])
    assert set(ps.sku_code) <= sku and set(ps.stockist_code) <= stk and set(ps.batch_no.dropna()) <= bat
    assert set(ec.sku_code) <= sku and set(ec.stockist_code) <= stk
    assert (~ec.batch_no.isin(bat)).sum() == 971            # older batches, documented (01 p3 s5.2)


def test_numbers_that_must_not_move():
    ps, ec = load("primary_sales"), load("expiry_claims")
    assert round(ps.net_value_inr.sum()) == 5_108_059_709
    assert round(ec.claim_value_derived_inr[ec.claim_value_was_derived].sum()) == 2_868_384
    q = fy_quarter(ps.invoice_date)
    assert round(ps.net_value_inr[q == "FY27Q1"].sum() / 1e7, 2) == 51.36      # QBR p1


def test_fy_quarter_labels():
    s = pd.Series(pd.to_datetime(["2026-04-01", "2026-06-30", "2026-07-01", "2026-12-31", "2027-01-01", "2027-03-31"]))
    assert fy_quarter(s).tolist() == ["FY27Q1", "FY27Q1", "FY27Q2", "FY27Q3", "FY27Q4", "FY27Q4"]


def test_wrong_folder_is_refused(tmp_path, monkeypatch):
    monkeypatch.setenv("PILOT_DATA_DIR", str(tmp_path))
    with pytest.raises(DataError):
        load("sku_master")
    with pytest.raises(KeyError):
        load("not_a_table")
