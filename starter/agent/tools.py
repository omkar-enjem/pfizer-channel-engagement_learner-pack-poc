"""Tools read the data pack. Exact facts come from here, never from the model.

The data files live in data/. Paths are built from this file's location so they work
the same on your laptop and on Vercel.
"""
import csv
from functools import lru_cache
from pathlib import Path

from langchain_core.tools import tool

DATA = Path(__file__).resolve().parent.parent / "data"


@lru_cache(maxsize=1)
def _batches() -> dict:
    """Batch master joined to the SKU master. Codes are cleaned so lookups do not miss."""
    with open(DATA / "sku_master.csv", newline="") as f:
        skus = {r["sku_code"].strip().upper(): r for r in csv.DictReader(f)}
    with open(DATA / "batch_master.csv", newline="") as f:
        out = {}
        for r in csv.DictReader(f):
            code = r["sku_code"].strip().upper()
            out[r["batch_no"].strip().upper()] = {**skus.get(code, {}), **r, "sku_code": code}
        return out


def batch_record(batch_no: str) -> dict:
    """Plain function: easy to test without a model."""
    row = _batches().get(batch_no.strip().upper())
    if row is None:
        return {"found": False, "batch_no": batch_no, "reason": "No such batch in the batch master"}
    return {"found": True, **row}


@tool
def lookup_batch(batch_no: str) -> dict:
    """Look up one batch in the batch master. Returns the SKU, product, manufacturing date,
    expiry date and price to stockist, or found=False if the batch does not exist.
    Use it whenever a question mentions a batch number."""
    return batch_record(batch_no)


TOOLS = [lookup_batch]
