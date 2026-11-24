"""Load the seven CLEAN tables for the pilot.

The cleaning itself is done once, in notebooks/step3_clean.ipynb, and is audited there
(data-clean/audit/). This module only READS the clean CSVs, gives every column its real type,
and checks it has been given the right files. It never changes a value and never fills a blank.

    from agent.data import load, load_all, fy_quarter
    claims = load("expiry_claims")

Where the files live: `data/` next to this package (committed, so Vercel can read it), or the
folder named in the environment variable PILOT_DATA_DIR. To refresh `data/` after re-running the
cleaning notebook:   python -m agent.data --sync ../data-clean
"""
from __future__ import annotations

import os
import shutil
import sys
from functools import lru_cache
from pathlib import Path

import pandas as pd

TABLES = ["sku_master", "stockist_master", "batch_master", "primary_sales",
          "cnf_stock_snapshot", "expiry_claims", "claim_emails"]

# Rows we expect in each clean table (from the cleaning audit, 24 Nov 2026). A wrong or stale
# folder is caught at load time instead of giving quietly wrong answers.
EXPECTED_ROWS = {"sku_master": 36, "stockist_master": 156, "batch_master": 663, "primary_sales": 93063,
                 "cnf_stock_snapshot": 5015, "expiry_claims": 4503, "claim_emails": 30}

DATE_COLS = {
    "stockist_master": ["appointed_on"],
    "batch_master": ["mfg_date", "expiry_date"],
    "primary_sales": ["invoice_date"],
    "cnf_stock_snapshot": ["snapshot_date", "expiry_date"],
    "expiry_claims": ["claim_date", "expiry_date_as_claimed", "credit_note_date"],
    "claim_emails": ["received_date"],
}
FLAG_COLS = {  # True / False columns written by the cleaning notebook
    "primary_sales": ["is_cancelled_line", "split_line_continuation", "same_batch_split_pick"],
    "cnf_stock_snapshot": ["is_stockout_row", "qty_conflict"],
    "expiry_claims": ["invoice_ref_missing", "claim_value_was_derived"],
}
# Columns every table must have, so a renamed or missing column fails loudly.
REQUIRED = {
    "sku_master": ["sku_code", "pts_inr", "mrp_inr", "shelf_life_months", "therapy_area"],
    "stockist_master": ["stockist_code", "cnf_code"],
    "batch_master": ["batch_no", "sku_code", "mfg_date", "expiry_date", "batch_qty_packs"],
    "primary_sales": ["invoice_no", "invoice_date", "stockist_code", "sku_code", "batch_no", "ordered_qty",
                      "invoiced_qty", "free_qty", "pts_inr", "net_value_inr", "scheme_code"],
    "cnf_stock_snapshot": ["snapshot_date", "cnf_code", "sku_code", "batch_no", "qty_on_hand_packs"],
    "expiry_claims": ["claim_no", "claim_date", "stockist_code", "sku_code", "batch_no", "qty_claimed",
                      "claim_value_inr", "claim_value_derived_inr", "claim_type", "status", "credit_note_no",
                      "credit_note_date", "credit_value_inr"],
    "claim_emails": ["email_id", "received_date", "subject", "body"],
}


class DataError(RuntimeError):
    """The data folder is missing, stale or not the cleaned data."""


def data_dir() -> Path:
    env = os.environ.get("PILOT_DATA_DIR")
    return Path(env) if env else Path(__file__).resolve().parent.parent / "data"


@lru_cache(maxsize=None)
def _load(name: str, folder: str) -> pd.DataFrame:
    path = Path(folder) / f"{name}.csv"
    if not path.is_file():
        raise DataError(f"{path} not found. Run notebooks/step3_clean.ipynb, then: python -m agent.data --sync ../data-clean")
    # Blanks stay blank (NaN). keep_default_na=False so a real text value such as 'NA' is never turned into a blank.
    df = pd.read_csv(path, keep_default_na=False, na_values=[""])
    for c in DATE_COLS.get(name, []):
        df[c] = pd.to_datetime(df[c], format="%Y-%m-%d", errors="raise")
    for c in FLAG_COLS.get(name, []):
        df[c] = df[c].astype(bool)
    missing = [c for c in REQUIRED[name] if c not in df.columns]
    if missing:
        raise DataError(f"{name}: columns missing {missing}. The data folder is not the cleaned data.")
    if len(df) != EXPECTED_ROWS[name]:
        raise DataError(f"{name}: {len(df)} rows, expected {EXPECTED_ROWS[name]}. Stale or wrong data folder: {folder}")
    return df


def load(name: str) -> pd.DataFrame:
    """One clean table, typed. The same object is returned on every call, so treat it as read-only."""
    if name not in TABLES:
        raise KeyError(f"unknown table {name!r}; choose from {TABLES}")
    return _load(name, str(data_dir()))


def load_all() -> dict[str, pd.DataFrame]:
    return {n: load(n) for n in TABLES}


def fy_quarter(dates: pd.Series) -> pd.Series:
    """Financial-year quarter label, e.g. 2026-05-10 -> 'FY27Q1' (Q1 = April to June; QBR p1)."""
    d = dates.dt
    fy = d.year.where(d.month < 4, d.year + 1)
    q = ((d.month - 4) % 12) // 3 + 1
    return "FY" + (fy % 100).astype(str) + "Q" + q.astype(str)


def sync_from(src: str | Path) -> list[str]:
    """Copy the seven clean CSVs from the cleaning notebook's output folder into the pilot's data/ folder."""
    src, dst = Path(src), data_dir()
    dst.mkdir(parents=True, exist_ok=True)
    copied = []
    for n in TABLES:
        s = src / f"{n}.csv"
        if not s.is_file():
            raise DataError(f"{s} not found. Run notebooks/step3_clean.ipynb first.")
        shutil.copyfile(s, dst / f"{n}.csv")
        copied.append(n)
    _load.cache_clear()
    for n in TABLES:  # prove the copy is good before anyone relies on it
        load(n)
    return copied


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--sync":
        print("copied and checked:", ", ".join(sync_from(sys.argv[2])), "->", data_dir())
    else:
        for n, df in load_all().items():
            print(f"{n:20s} {len(df):>7,} rows  {df.shape[1]:>2} columns")
