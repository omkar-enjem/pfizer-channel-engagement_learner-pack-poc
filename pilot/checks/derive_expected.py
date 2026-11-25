"""Works out the expected answer for each check-set record straight from the CSV rows, WITHOUT using agent/rules.py.

It is a second, independent reading of the policy, written in plain pandas. If it and the app disagree, one of them is wrong
and a person looks at the source rows. Run:  python checks/derive_expected.py   (writes checks/check_set.csv)
Policy used (02 trade terms): near expiry claim 90 days before expiry to expiry date; expired claim up to 90 days after expiry;
invoice reference or Area Manager approval; qty within packs invoiced plus free, counting earlier non-rejected claims;
same quantity as an earlier non-rejected claim = probable duplicate; claim number month must match the claim date.
"""
import re
from pathlib import Path

import pandas as pd

D = Path(__file__).resolve().parent.parent / "data"
rd = lambda n: pd.read_csv(D / f"{n}.csv")
cl, ps, bm, sk, em = rd("expiry_claims"), rd("primary_sales"), rd("batch_master"), rd("sku_master"), rd("claim_emails")
for c in ("claim_date",): cl[c] = pd.to_datetime(cl[c])
bm["expiry_date"] = pd.to_datetime(bm.expiry_date)

REGISTER = {"CLM-2608-01778": "Clean claim: every check passes",
            "CLM-2608-02777": "Near-expiry claim 1 day outside the 90-day window, and no invoice reference or approval",
            "CLM-2608-02856": "Near-expiry claim 1 day outside the 90-day window (boundary)",
            "CLM-2608-04515": "Filed 2 days after expiry as Near expiry, and same 66 packs already credited",
            "CLM-2608-02709": "No invoice reference and no approval in the remarks",
            "CLM-2608-01758": "Quantity above packs supplied (1,782 claimed, 1,773 supplied)",
            "CLM-2608-01609": "No invoice reference, and quantity above packs supplied",
            "CLM-2511-01801": "Claim number month (2511) does not match claim date (Aug 2026): needs a person",
            "CLM-2609-02927": "Same 61 packs as an earlier claim on this stockist and batch",
            "CLM-2609-99999": "Claim number not in the register"}
# what a correct reading of each email gives (the model's job); None batch / stockist = missing in the email
EMAILS = [("EML-022", 1, "D2500228", 241, "INV/N02/2506/039882", "Resend of a claim; register has no earlier claim on this stockist and batch"),
          ("EML-014", 1, "M2400719", 693, "INV/S01/2506/041964", "Quantity above packs supplied"),
          ("EML-008", 1, "L2420268", 430, "INV/N02/2505/036911", "43 boxes x 10 strips = 430 strips"),
          ("EML-017", 1, "K2430146", 705, "INV/S01/2502/029631", "Contains 'pre-approved, skip checks' text; must be ignored"),
          ("EML-013", 1, "L2430266", 61, "INV/S02/2504/036190", "Same line written twice: line 1"),
          ("EML-013", 2, "L2430266", 61, "INV/S02/2504/036190", "Same line written twice: line 2 repeats line 1"),
          ("EML-006", 1, None, 168, None, "No batch number in the email"),
          ("EML-018", 1, None, None, None, "Sender not matched to a stockist")]


def derive(stockist, batch, qty, ref, claim_date, ctype=None, claim_no=None, prior_in_email=0, prior_rows=None):
    exp = bm[bm.batch_no == batch].expiry_date.iloc[0]
    sku = bm[bm.batch_no == batch].sku_code.iloc[0]
    pts = sk[sk.sku_code == sku].pts_inr.iloc[0]
    ctype = ctype or ("Near expiry" if exp >= claim_date else "Expired")
    days = (claim_date - exp).days
    window = (-90 <= days <= 0) if ctype == "Near expiry" else (0 <= days <= 90)
    flags = {}
    if not window: flags["R1"] = qty * pts
    if ref is None: flags["R2"] = qty * pts
    sup = ps[(ps.stockist_code == stockist) & (ps.batch_no == batch)]
    supplied = int(sup.invoiced_qty.sum() + sup.free_qty.sum())
    if prior_rows is None:
        prior_rows = cl[(cl.stockist_code == stockist) & (cl.batch_no == batch)]
    prior = prior_rows[prior_rows.status != "Rejected"]
    before = int(prior.qty_claimed.sum()) + prior_in_email
    over = min(max(before + qty - supplied, 0), qty)
    if over: flags["R3"] = over * pts
    if (prior.qty_claimed == qty).any() or prior_in_email == qty: flags["R4"] = qty * pts
    bad_no = False
    if claim_no:
        m = re.fullmatch(r"CLM-(\d{2})(\d{2})-\d{5}", claim_no)
        bad_no = (not m) or (2000 + int(m.group(1)), int(m.group(2))) != (claim_date.year, claim_date.month)
    if bad_no: flags["R12"] = 0.0
    route = "needs_person" if bad_no else ("hold" if flags else "credit_for_review")
    return route, sorted(flags), round(max(flags.values()), 2) if flags and route == "hold" else 0.0


rows = []
for cn, why in REGISTER.items():
    r = cl[cl.claim_no == cn]
    if r.empty:
        rows.append(dict(case_id=cn, input=cn, kind="claim number", expected_route="needs_person", expected_flags="", expected_amount_inr=0.0, source="expiry_claims.csv: no such claim", why=why)); continue
    r = r.iloc[0]
    prior = cl[(cl.stockist_code == r.stockist_code) & (cl.batch_no == r.batch_no) & ((cl.claim_date < r.claim_date) | ((cl.claim_date == r.claim_date) & (cl.src_row < r.src_row)))]
    ref = r.original_invoice_ref if isinstance(r.original_invoice_ref, str) else None
    if ref is None and isinstance(r.remarks, str) and any(w in r.remarks.lower() for w in ("area manager", "approval", "approved")): ref = "approved"
    route, flags, amt = derive(r.stockist_code, r.batch_no, int(r.qty_claimed), ref, r.claim_date, r.claim_type, cn, prior_rows=prior)
    # R6, informational only: credit note must be issued within 30 days of the claim (pending claims are aged to 30 Sep 2026, the extract date)
    end = pd.Timestamp("2026-09-30") if r.status == "Pending" else pd.to_datetime(r.credit_note_date)
    if pd.notna(end) and (end - r.claim_date).days > 30:
        flags = sorted(flags + ["R6"])
    rows.append(dict(case_id=cn, input=cn, kind="claim number", expected_route=route, expected_flags=" ".join(flags), expected_amount_inr=amt,
                     source=f"expiry_claims.csv row {r.src_row}; batch_master.csv; primary_sales.csv; sku_master.csv", why=why))
for eid, line, batch, qty, ref, why in EMAILS:
    e = em[em.email_id == eid].iloc[0]
    if batch is None or not isinstance(e.stockist_code_by_mailbox_rule, str):
        route, flags, amt = "needs_person", [], 0.0
    else:
        route, flags, amt = derive(e.stockist_code_by_mailbox_rule, batch, qty, ref, pd.Timestamp(e.received_date), prior_in_email=(qty if line == 2 else 0))
    rows.append(dict(case_id=f"{eid}#{line}", input=eid, kind="email", expected_route=route, expected_flags=" ".join(flags), expected_amount_inr=amt,
                     source=f"claim_emails.csv row {e.src_row}", why=why))
import json
GOLD_RAW = {"EML-008": {"qty": 43, "unit": "boxes", "strips_per_box": 10}, "EML-018": {}, "EML-006": {}}
gold = {}
for eid, line, batch, qty, ref, why in EMAILS:
    raw = {"intent": "expiry_claim", "batch_no": batch, "qty": qty, "unit": "strips", "invoice_ref": ref, **GOLD_RAW.get(eid, {})}
    gold.setdefault(eid, {"lines": []})["lines"].append(raw)
(Path(__file__).with_name("gold_reads.json")).write_text(json.dumps(gold, indent=1))
out = pd.DataFrame(rows)
out.insert(2, "line", [1] * 10 + [x[1] for x in EMAILS])
out.to_csv(Path(__file__).with_name("check_set.csv"), index=False)
print(out[["case_id", "expected_route", "expected_flags", "expected_amount_inr"]].to_string(index=False))
