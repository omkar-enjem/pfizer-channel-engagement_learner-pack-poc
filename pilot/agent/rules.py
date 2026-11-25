"""The claim rules, as plain Python. No model, no data files: inputs in, a Check out.

Each rule returns a Check with a status:
    pass          the claim is inside the rule
    flag          the claim breaks the rule (a person still decides; nothing is rejected here)
    not_testable  the data needed to test the rule is missing, so we do not guess
    needs_person  the inputs contradict each other or cannot be trusted
Limits and page references live in config.py. Each rule has tests in tests/test_rules.py.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import timedelta

import config as C

PASS, FLAG, NOT_TESTABLE, NEEDS_PERSON = "pass", "flag", "not_testable", "needs_person"


@dataclass
class Check:
    rule: str
    status: str
    summary: str
    amount_inr: float = 0.0          # rupees at issue when this rule is flagged
    amount_basis: str = "none"       # "claim" = the whole claim value, "excess" = value of excess packs only
    detail: dict = field(default_factory=dict)

    @property
    def clause(self) -> str:
        return C.CLAUSES[self.rule]

    def as_dict(self) -> dict:
        d = asdict(self)
        d["clause"] = self.clause
        return d


def _blank(v) -> bool:
    return v is None or (isinstance(v, float) and v != v) or str(v).strip() == ""


def r1_window(claim_type, claim_date, expiry_date, invoice_date=None) -> Check:
    """02 p3 s5.2. Near expiry: -90..0 days from expiry. Expired: 0..+90. Breakage or short supply: 0..7 days from invoice."""
    if claim_type in (C.NEAR_EXPIRY, C.EXPIRED):
        d = (claim_date - expiry_date).days
        lo, hi = (-C.NEAR_EXPIRY_DAYS_BEFORE, 0) if claim_type == C.NEAR_EXPIRY else (0, C.EXPIRED_DAYS_AFTER)
        what = "days from expiry"
    elif claim_type in (C.BREAKAGE, C.SHORT_SUPPLY):
        if invoice_date is None:
            return Check("R1", NOT_TESTABLE, "No invoice date, so the 7-day window cannot be tested")
        d = (claim_date - invoice_date).days
        lo, hi = 0, C.BREAKAGE_DAYS_AFTER_INVOICE
        what = "days from invoice"
    else:
        return Check("R1", NEEDS_PERSON, f"Unknown claim type {claim_type!r}")
    detail = {"claim_type": claim_type, what: d, "allowed_from": lo, "allowed_to": hi}
    if lo <= d <= hi:
        return Check("R1", PASS, f"{claim_type}: {d} {what}, inside {lo} to {hi}", detail=detail)
    return Check("R1", FLAG, f"{claim_type}: {d} {what}, outside {lo} to {hi}", amount_basis="claim", detail=detail)


def r2_invoice_reference(invoice_ref, remarks=None, invoice_found=None) -> Check:
    """02 p3 s5.3-5.4. An invoice reference is needed, or the Area Manager's written approval."""
    if not _blank(invoice_ref):
        if invoice_found is False:
            return Check("R2", NEEDS_PERSON, f"Invoice {invoice_ref} is not in the sales file", detail={"invoice_ref": invoice_ref})
        return Check("R2", PASS, f"Quotes invoice {invoice_ref}", detail={"invoice_ref": invoice_ref})
    text = "" if _blank(remarks) else str(remarks).lower()
    if any(w in text for w in C.APPROVAL_WORDS):
        return Check("R2", PASS, "No invoice reference, but the remarks record an approval", detail={"remarks": remarks})
    return Check("R2", FLAG, "No invoice reference and no recorded approval (the approval may exist outside the file)",
                 amount_basis="claim", detail={"remarks": None if _blank(remarks) else remarks})


def r3_quantity(qty_claimed, supplied, claimed_before, pts) -> Check:
    """02 p3 s5.5. Packs claimed on a batch must not exceed packs invoiced to that stockist for it, free packs included.
    claimed_before = packs in earlier claims on the same stockist and batch that were not rejected."""
    if supplied is None:
        return Check("R3", NOT_TESTABLE, "No invoice of this batch to this stockist in the sales file")
    excess = min(max(claimed_before + qty_claimed - supplied, 0), qty_claimed)
    detail = {"qty_claimed": qty_claimed, "packs_supplied": supplied, "claimed_before": claimed_before, "excess_packs": excess}
    if excess == 0:
        return Check("R3", PASS, f"{qty_claimed} claimed, {supplied} supplied, {claimed_before} claimed earlier", detail=detail)
    return Check("R3", FLAG, f"{excess} packs above the {supplied} supplied (this claim {qty_claimed}, earlier claims {claimed_before})",
                 amount_inr=round(excess * pts, 2), amount_basis="excess", detail=detail)


def r4_repeat(qty_claimed, earlier) -> Check:
    """02 p4 s5.6 and 03 p3 s2.6. No earlier claim on the same stockist and batch.
    earlier = list of (qty, status) for earlier claims on the same stockist and batch.
    Only a same-quantity repeat of a claim that was not rejected is flagged: a different quantity can be a genuine part-return."""
    earlier = list(earlier)
    dup = [q for q, s in earlier if q == qty_claimed and s != "Rejected"]
    detail = {"earlier_claims": len(earlier), "same_quantity_not_rejected": len(dup)}
    if dup:
        return Check("R4", FLAG, f"Probable duplicate: {len(dup)} earlier claim(s) on this stockist and batch for the same {qty_claimed} packs",
                     amount_basis="claim", detail=detail)
    if earlier:
        return Check("R4", PASS, f"{len(earlier)} earlier claim(s) on this batch, none for the same quantity", detail=detail)
    return Check("R4", PASS, "No earlier claim on this stockist and batch", detail=detail)


def r5_value(qty_claimed, pts, recorded_value=None) -> Check:
    """02 p4 s5.7. Claim value = quantity x PTS. The extract holds one price per SKU, so PTS on the claim date cannot be tested separately."""
    expected = round(qty_claimed * pts, 2)
    if _blank(recorded_value):
        return Check("R5", PASS, f"No recorded value; derived {expected:.2f} = {qty_claimed} x {pts}", detail={"expected_inr": expected, "recorded_inr": None})
    ok = abs(expected - float(recorded_value)) < C.VALUE_TOLERANCE_INR
    detail = {"expected_inr": expected, "recorded_inr": float(recorded_value)}
    if ok:
        return Check("R5", PASS, f"Value {float(recorded_value):.2f} = {qty_claimed} x {pts}", detail=detail)
    return Check("R5", FLAG, f"Recorded value {float(recorded_value):.2f}, expected {expected:.2f}", detail=detail)


def r6_clock(claim_date, credit_note_date=None, asof=None) -> Check:
    """02 p4 s5.6. Credit note within 30 days of receipt. claim_date stands in for the date of receipt."""
    limit = C.CREDIT_NOTE_DAYS
    due = claim_date + timedelta(days=limit)
    if credit_note_date is not None:
        days = (credit_note_date - claim_date).days
        detail = {"days_to_credit_note": days, "limit_days": limit}
        if days > limit:
            return Check("R6", FLAG, f"Credit note took {days} days; the limit is {limit}", detail=detail)
        return Check("R6", PASS, f"Credit note in {days} days, inside {limit}", detail=detail)
    detail = {"credit_note_due": due.strftime("%Y-%m-%d"), "limit_days": limit}
    if asof is not None and (asof - claim_date).days > limit:
        return Check("R6", FLAG, f"Pending {(asof - claim_date).days} days; the credit note was due by {detail['credit_note_due']}", detail=detail)
    return Check("R6", PASS, f"Credit note due by {detail['credit_note_due']}", detail=detail)


def r12_claim_number(claim_no, claim_date) -> Check:
    """03 p3 s2.6. Claim number CLM-yymm-nnnnn, assigned when the claim arrives. If its month differs from the claim date, which date is true needs a person."""
    m = re.match(C.CLAIM_NO_PATTERN, "" if _blank(claim_no) else str(claim_no))
    if not m:
        return Check("R12", NEEDS_PERSON, f"Claim number {claim_no!r} is not in the format CLM-yymm-nnnnn")
    yy, mm = int(m.group(1)), int(m.group(2))
    detail = {"claim_no": claim_no, "number_month": f"20{yy:02d}-{mm:02d}", "claim_date_month": claim_date.strftime("%Y-%m")}
    if (2000 + yy, mm) != (claim_date.year, claim_date.month):
        return Check("R12", NEEDS_PERSON, f"Claim number says {detail['number_month']} but the claim date is {claim_date.strftime('%Y-%m-%d')}: which date is true?", detail=detail)
    return Check("R12", PASS, "Claim number month matches the claim date", detail=detail)


def decide(checks, claim_value_inr=None) -> dict:
    """Route the claim. needs_person beats hold, hold beats credit_for_review.
    Rupees at issue are the largest single flagged amount, never a sum, because the rules overlap."""
    checks = list(checks)
    blocking = [c for c in checks if c.rule in C.BLOCKING_RULES]
    if any(c.status == NEEDS_PERSON for c in checks):
        route, why = C.NEEDS_PERSON, [c for c in checks if c.status == NEEDS_PERSON]
    elif any(c.status == FLAG for c in blocking):
        route, why = C.HOLD, [c for c in blocking if c.status == FLAG]
    elif any(c.status == NOT_TESTABLE for c in blocking):
        route, why = C.NEEDS_PERSON, [c for c in blocking if c.status == NOT_TESTABLE]
    else:
        route, why = C.CREDIT_FOR_REVIEW, []
    amount = 0.0
    if route == C.HOLD:
        amount = max((c.amount_inr if c.amount_basis == "excess" else (claim_value_inr or 0.0)) for c in why)
    return {"route": route, "reasons": [f"{c.rule}: {c.summary}" for c in why], "amount_at_issue_inr": round(float(amount), 2),
            "informational": [f"{c.rule}: {c.summary}" for c in checks if c.status == FLAG and c.rule not in C.BLOCKING_RULES]}
