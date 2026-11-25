"""Every policy number the pilot uses, with the document and page it came from.

No rule number may appear anywhere else in the code or in a prompt. To change a limit, change it
here and re-run `pytest -q`. Documents: 02 = trade terms and claims policy, 03 = C&F agreement.
Page and section references are the ones verified in notes/rules.md (23 Nov 2026).
"""

# --- R1: claim windows (02 p3 section 5.2) -------------------------------------------------------
NEAR_EXPIRY = "Near expiry"
EXPIRED = "Expired"
BREAKAGE = "Breakage in transit"
SHORT_SUPPLY = "Short supply"
NEAR_EXPIRY_DAYS_BEFORE = 90      # near-expiry claim: from 90 days before expiry up to the expiry date
EXPIRED_DAYS_AFTER = 90           # expired claim: from the expiry date up to 90 days after it
BREAKAGE_DAYS_AFTER_INVOICE = 7   # breakage or short supply: within 7 days of the invoice

# --- R6: credit note timing (02 p4 section 5.6) ----------------------------------------------------
CREDIT_NOTE_DAYS = 30             # credit note within 30 days of receipt of the claim
VERIFY_WORKING_DAYS = 10          # C&F verification within 10 working days (not testable: no verification date)

# --- Date of the data pack (last day of the extract). Pending claims are aged to this date, never to today. ---
from datetime import date
DATA_AS_OF = date(2026, 9, 30)    # 01 p1: extract covers 1 Apr 2024 to 30 Sep 2026

# --- R5: valuation (02 p4 section 5.7) -------------------------------------------------------------
VALUE_TOLERANCE_INR = 0.01        # claim value must equal quantity x PTS to the paisa

# --- R12: claim number format (03 p3 section 2.6) --------------------------------------------------
CLAIM_NO_PATTERN = r"^CLM-(\d{2})(\d{2})-(\d{5})$"   # CLM-yymm-nnnnn

# --- R2: approval wording searched in the remarks (02 p3 sections 5.3 and 5.4) ---------------------
APPROVAL_WORDS = ("area manager", "approval", "approved")

# --- Where each rule comes from, shown next to every result on screen ------------------------------
CLAUSES = {
    "R1": "02 p3 s5.2 claim windows",
    "R2": "02 p3 s5.3-5.4 invoice reference or Area Manager approval",
    "R3": "02 p3 s5.5 quantity within packs invoiced, free packs included",
    "R4": "02 p4 s5.6 and 03 p3 s2.6 no earlier claim on the same stockist and batch",
    "R5": "02 p4 s5.7 valued at PTS",
    "R6": "02 p4 s5.6 credit note within 30 days of receipt",
    "R12": "03 p3 s2.6 claim number format CLM-yymm-nnnnn",
}

# --- Which rules can put a claim on hold. R5 and R6 inform; they do not hold a claim. ---------------
BLOCKING_RULES = ("R1", "R2", "R3", "R4")

# --- Routes the graph can end in ----------------------------------------------------------------
CREDIT_FOR_REVIEW = "credit_for_review"
HOLD = "hold"
NEEDS_PERSON = "needs_person"
