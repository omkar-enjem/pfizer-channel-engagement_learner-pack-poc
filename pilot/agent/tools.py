"""Lookups: exact facts read from the data files. Each answer carries the file and row it came from.

No model is involved here. The CSVs are loaded once (agent/data.py) and indexed in memory.
`src_row` is the line number of the record in the original pack file, so a person can open that
file and confirm the value (Ctrl+G in VS Code).
"""
from __future__ import annotations

from functools import lru_cache

import pandas as pd

from agent.data import load

CLAIM_COLS = ["src_row", "claim_no", "claim_date", "stockist_code", "cnf_code", "sku_code", "batch_no", "expiry_date_as_claimed",
              "qty_claimed", "claim_value_inr", "claim_value_derived_inr", "claim_type", "original_invoice_ref", "status",
              "credit_note_no", "credit_note_date", "credit_value_inr", "remarks"]


def py(v):
    """Plain Python value: NaN and NaT become None, numpy numbers become int or float."""
    if v is None or (not isinstance(v, str) and pd.isna(v)):
        return None
    if hasattr(v, "item"):
        return v.item()
    return v


def _record(row: pd.Series, cols=None) -> dict:
    return {c: py(row[c]) for c in (cols or row.index)}


@lru_cache(maxsize=1)
def _claims() -> dict:
    df = load("expiry_claims")
    assert df.claim_no.is_unique, "claim_no must be unique"
    return {r["claim_no"]: {c: (r[c] if c in ("claim_date", "expiry_date_as_claimed", "credit_note_date") and pd.notna(r[c]) else py(r[c])) for c in CLAIM_COLS}
            for _, r in df[CLAIM_COLS].iterrows()}


@lru_cache(maxsize=1)
def _pair_history() -> dict:
    """(stockist, batch) -> claims in the order the register was filled: claim date, then source row."""
    hist: dict = {}
    for c in sorted(_claims().values(), key=lambda c: (c["claim_date"], c["src_row"])):
        hist.setdefault((c["stockist_code"], c["batch_no"]), []).append(c)
    return hist


@lru_cache(maxsize=1)
def _supply() -> dict:
    ps = load("primary_sales")
    ps = ps[ps.batch_no.notna()]
    g = ps.groupby(["stockist_code", "batch_no"]).agg(invoiced=("invoiced_qty", "sum"), free=("free_qty", "sum"), src_rows=("src_row", list))
    return {k: {"invoiced": int(r.invoiced), "free": int(r.free), "supplied": int(r.invoiced + r.free), "src_rows": [int(x) for x in r.src_rows]}
            for k, r in zip(g.index, g.itertuples())}


@lru_cache(maxsize=1)
def _invoices() -> dict:
    g = load("primary_sales").groupby("invoice_no").agg(invoice_date=("invoice_date", "min"), src_rows=("src_row", list))
    return {k: {"invoice_date": r.invoice_date, "src_rows": [int(x) for x in r.src_rows]} for k, r in zip(g.index, g.itertuples())}


@lru_cache(maxsize=None)
def _by_key(table: str, key: str) -> dict:
    df = load(table)
    return {r[key]: _record(r) for _, r in df.iterrows()}


def find_claim(claim_no: str):
    """The claim row from expiry_claims.csv, or None."""
    return _claims().get(str(claim_no).strip().upper())


def claims_before(claim: dict) -> list[dict]:
    """Earlier claims on the same stockist and batch, in register order."""
    hist = _pair_history().get((claim["stockist_code"], claim["batch_no"]), [])
    return hist[:hist.index(claim)]


def claims_for_pair(stockist_code: str, batch_no: str) -> list[dict]:
    """Every claim already in the register for this stockist and batch (used for claims that are not in the register yet)."""
    return list(_pair_history().get((stockist_code, batch_no), []))


def supply(stockist_code: str, batch_no: str):
    """Packs Pfizer invoiced and gave free to this stockist on this batch (primary_sales.csv), or None."""
    return _supply().get((stockist_code, batch_no))


def invoice(invoice_no: str):
    """Invoice date and the rows of that invoice in primary_sales.csv, or None."""
    return _invoices().get(invoice_no)


def batch(batch_no: str):
    return _by_key("batch_master", "batch_no").get(batch_no)


def sku(sku_code: str):
    return _by_key("sku_master", "sku_code").get(sku_code)


def stockist(stockist_code: str):
    return _by_key("stockist_master", "stockist_code").get(stockist_code)
