"""Run every rule on one claim and collect the evidence. Plain Python: no model, no network."""
from __future__ import annotations

import pandas as pd

import config as C
from agent import rules as R
from agent import tools as T

MAX_ROWS = 10      # evidence lists show at most this many source rows


def iso(v):
    return v.strftime("%Y-%m-%d") if hasattr(v, "strftime") else v


def _ev(fact, file, rows, values):
    rows = list(rows)
    return {"fact": fact, "file": file, "rows": rows[:MAX_ROWS], "row_count": len(rows), "values": {k: iso(v) for k, v in values.items()}}


def not_found(claim_no) -> dict:
    return {"found": False, "claim_no": claim_no, "claim": None, "checks": [], "evidence": [],
            "decision": {"route": C.NEEDS_PERSON, "reasons": [f"Claim {claim_no} is not in the claims file"], "amount_at_issue_inr": 0.0, "informational": []}}


ALL_RULES = ("R1", "R2", "R3", "R4", "R5", "R6", "R12")
EMAIL_RULES = ("R1", "R2", "R3", "R4", "R5")     # no claim number yet, so no R6 clock and no R12 format check


def gather(claim: dict, source_evidence: dict | None = None, extra_earlier: list | None = None) -> dict:
    """Fetch every record the rules need for one claim. `claim` is a register row or a claim built from an email."""
    ref = claim["original_invoice_ref"]
    inv = T.invoice(ref) if ref else None
    bm, sk = T.batch(claim["batch_no"]), T.sku(claim["sku_code"])
    sup = T.supply(claim["stockist_code"], claim["batch_no"]) if bm else None
    in_register = claim.get("claim_no") is not None
    earlier = T.claims_before(claim) if in_register else T.claims_for_pair(claim["stockist_code"], claim["batch_no"])
    earlier = earlier + (extra_earlier or [])
    claimed_before = sum(e["qty_claimed"] for e in earlier if e["status"] != "Rejected")
    value = claim["claim_value_inr"] if claim["claim_value_inr"] is not None else claim["claim_value_derived_inr"]
    return {"claim": claim, "ref": ref, "inv": inv, "bm": bm, "sk": sk, "sup": sup, "earlier": earlier,
            "claimed_before": claimed_before, "pts": sk["pts_inr"], "value": value, "in_register": in_register,
            "source_evidence": source_evidence}


def run_rule(rule: str, f: dict) -> R.Check:
    c, inv, ref = f["claim"], f["inv"], f["ref"]
    if rule == "R1":
        return R.r1_window(c["claim_type"], c["claim_date"], c["expiry_date_as_claimed"], inv["invoice_date"] if inv else None)
    if rule == "R2":
        return R.r2_invoice_reference(ref, c["remarks"], invoice_found=(inv is not None) if ref else None)
    if rule == "R3":
        return R.r3_quantity(c["qty_claimed"], f["sup"]["supplied"] if f["sup"] else None, f["claimed_before"], f["pts"])
    if rule == "R4":
        return R.r4_repeat(c["qty_claimed"], [(e["qty_claimed"], e["status"]) for e in f["earlier"]])
    if rule == "R5":
        return R.r5_value(c["qty_claimed"], f["pts"], c["claim_value_inr"])
    if rule == "R6":
        return R.r6_clock(c["claim_date"], c["credit_note_date"], pd.Timestamp(C.DATA_AS_OF) if c["status"] == "Pending" else None)
    if rule == "R12":
        return R.r12_claim_number(c["claim_no"], c["claim_date"])
    raise ValueError(rule)


def rules_for(f: dict) -> tuple:
    return ALL_RULES if f["in_register"] else EMAIL_RULES


def evidence_for(f: dict) -> list:
    c, inv, sup, bm, sk, earlier = f["claim"], f["inv"], f["sup"], f["bm"], f["sk"], f["earlier"]
    ev = []
    if f["in_register"]:
        ev.append(_ev("The claim", "expiry_claims.csv", [c["src_row"]],
                      {k: c[k] for k in ("claim_no", "claim_date", "claim_type", "status", "stockist_code", "batch_no", "qty_claimed", "original_invoice_ref", "remarks")}))
    elif f.get("source_evidence"):
        s = f["source_evidence"]
        ev.append(_ev(s["fact"], s["file"], s["rows"], s["values"]))
    if inv:
        ev.append(_ev("Invoice quoted on the claim", "primary_sales.csv", inv["src_rows"], {"invoice_no": f["ref"], "invoice_date": inv["invoice_date"]}))
    if sup:
        ev.append(_ev("Packs supplied to this stockist on this batch", "primary_sales.csv", sup["src_rows"],
                      {"invoiced_qty": sup["invoiced"], "free_qty": sup["free"], "supplied": sup["supplied"]}))
    if bm:
        ev.append(_ev("Batch", "batch_master.csv", [bm["src_row"]], {"batch_no": bm["batch_no"], "expiry_date": bm["expiry_date"]}))
    ev.append(_ev("Price to stockist (PTS)", "sku_master.csv", [sk["src_row"]], {"sku_code": sk["sku_code"], "pts_inr": f["pts"]}))
    if earlier:
        ev.append(_ev("Earlier claims on this stockist and batch", "expiry_claims.csv", [e["src_row"] for e in earlier if e["src_row"] is not None],
                      {"claims": ", ".join(f"{e['claim_no']} ({e['qty_claimed']}, {e['status']})" for e in earlier[:MAX_ROWS])}))
    return ev


def claim_out(claim: dict, value) -> dict:
    out = {k: iso(v) for k, v in claim.items()}
    out["claim_value_used_inr"] = value
    return out


def check_claim(claim_no: str) -> dict:
    claim = T.find_claim(claim_no)
    if claim is None:
        return not_found(claim_no)
    f = gather(claim)
    checks = [run_rule(r, f) for r in rules_for(f)]
    return {"found": True, "claim_no": claim["claim_no"], "claim": claim_out(claim, f["value"]), "checks": [c.as_dict() for c in checks],
            "decision": R.decide(checks, f["value"]), "evidence": evidence_for(f)}
