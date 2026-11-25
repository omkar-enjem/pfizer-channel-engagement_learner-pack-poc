"""Batch run: every non-rejected claim of the last 12 months (1 Oct 2025 to 30 Sep 2026) through the rules. No model, no network.

  python checks/batch_12m.py      prints the table used on the deck's money slide and writes checks/batch_12m_results.csv
Claim value = recorded value, or quantity x PTS where the register has none (62 claims). 'Held' is not 'recovered':
discovery sizes what is recoverable at 0.3 to 0.5 crore a year if no approved exception exists.
"""
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from agent import check as K  # noqa: E402
from agent.data import load  # noqa: E402

cl = load("expiry_claims")
w = cl[(cl.claim_date >= "2025-10-01") & (cl.claim_date <= "2026-09-30") & (cl.status != "Rejected")]
rows = []
for cn in w.claim_no:
    r = K.check_claim(cn)
    st = {c["rule"]: c["status"] for c in r["checks"]}
    rows.append(dict(claim_no=cn, status=r["claim"]["status"], route=r["decision"]["route"], amount_at_issue_inr=r["decision"]["amount_at_issue_inr"],
                     claim_value_inr=r["claim"]["claim_value_used_inr"] or 0, **{k: st[k] for k in ("R1", "R2", "R3", "R4", "R6", "R12")}))
df = pd.DataFrame(rows)
df.to_csv(HERE / "batch_12m_results.csv", index=False)
cr = lambda m: df.claim_value_inr[m].sum() / 1e7
print(f"{len(df)} claims, claim value {cr(df.claim_no.notna()):.2f} crore\n")
for route in ("credit_for_review", "hold", "needs_person"):
    m = df.route == route
    print(f"{route:18s} {m.sum():5d} claims ({m.mean()*100:4.1f}%)  value {cr(m):.2f} crore")
core = (df.R1 == "flag") | (df.R3 == "flag") | (df.R4 == "flag")
print(f"\nbreaks a written limit (R1, R3 or R4): {core.sum()} claims, {cr(core):.3f} crore; already credited {(core & (df.status == 'Credited')).sum()} claims, {cr(core & (df.status == 'Credited')):.2f} crore")
r2 = df.R2 == "flag"
print(f"no invoice reference or approval (R2): {r2.sum()} claims, {cr(r2):.3f} crore (overlaps the line above: never add)")
only = r2 & ~core
print(f"  held only for R2: {only.sum()} claims, {cr(only):.2f} crore")
print(f"R12 needs a person: {(df.R12 == 'needs_person').sum()} claims, {cr(df.R12 == 'needs_person'):.2f} crore")
