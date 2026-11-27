"""The three tables behind the discovery note's charts, so every plotted number can be re-made.

  python checks/discovery_charts.py     prints the tables and writes checks/discovery_chart_*.csv

1. trend: expiry claim value by calendar quarter (non-rejected claims; value = recorded claim value, or quantity x PTS where none is recorded)
2. split: the 12-month claim money in three groups (G1 breaks R1, R3 or R4; G2 scheme batch with no rule broken; G3 the rest), the same groups as notebooks/step4_recovery
3. r1_rates: share of R1 (claim window) flags by claim type, 12 months to 30 Sep 2026, from checks/batch_12m_results.csv (run batch_12m.py first)
"""
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from agent.data import load  # noqa: E402

cl, sk = load("expiry_claims"), load("sku_master")
cl = cl[cl.status != "Rejected"].merge(sk[["sku_code", "pts_inr"]], on="sku_code", how="left")
cl["value"] = cl.claim_value_inr.fillna(cl.qty_claimed * cl.pts_inr)

q = cl.groupby(cl.claim_date.dt.to_period("Q")).agg(claims=("claim_no", "size"), value_cr=("value", lambda s: s.sum() / 1e7)).reset_index()
q["quarter"] = q.claim_date.dt.year.astype(str) + " Q" + q.claim_date.dt.quarter.astype(str)
trend = q[["quarter", "claims", "value_cr"]].round({"value_cr": 3})
last4 = trend.tail(4)
print("1. trend (claim value, crore)\n", trend.to_string(index=False), f"\n   last four quarters: {last4.value_cr.sum():.2f} crore, {int(last4.claims.sum())} claims\n")
trend.to_csv(HERE / "discovery_chart_trend.csv", index=False)

import numpy as np  # noqa: E402

res = pd.read_csv(HERE / "batch_12m_results.csv")
flagged = set(res[(res.R1 == "flag") | (res.R3 == "flag") | (res.R4 == "flag")].claim_no)
w = cl[(cl.claim_date >= "2025-10-01") & (cl.claim_date <= "2026-09-30")].copy()
w["amount"] = np.where(w.status == "Credited", w.credit_value_inr, w.value)            # paid, or still owed
ps = load("primary_sales")
ps = ps[ps.batch_no.notna()]
sb = ps.assign(sch=ps.scheme_code.fillna("NA") != "NO_SCHEME").groupby(["stockist_code", "batch_no"]).sch.max().reset_index()
w = w.merge(sb, on=["stockist_code", "batch_no"], how="left")
w["group"] = np.where(w.claim_no.isin(flagged), "G1 breaks a written rule", np.where(w.sch == True, "G2 linked to a scheme batch", "G3 the rest"))  # noqa: E712
split = w.groupby("group").agg(claims=("claim_no", "size"), value_cr=("amount", lambda s: s.sum() / 1e7)).reset_index().round({"value_cr": 4})
split["share_of_value"] = (split.value_cr / split.value_cr.sum()).round(3)
print("2. split (discovery basis: credit note value for credited, claim value for pending; same groups as notebooks/step4_recovery)\n", split.to_string(index=False),
      f"\n   total {split.value_cr.sum():.3f} crore, {int(split.claims.sum())} claims\n")
split.to_csv(HERE / "discovery_chart_split.csv", index=False)

r = pd.read_csv(HERE / "batch_12m_results.csv").merge(load("expiry_claims")[["claim_no", "claim_type"]], on="claim_no")
rows = []
for t, d in r.groupby("claim_type"):
    tested = d[d.R1 != "not_testable"]
    rows.append(dict(claim_type=t, tested=len(tested), flagged=int((tested.R1 == "flag").sum()), not_testable=int((d.R1 == "not_testable").sum())))
rates = pd.DataFrame(rows)
rates["flag_rate"] = (rates.flagged / rates.tested).round(3)
rates = rates.sort_values("flag_rate", ascending=False)
print("3. R1 flag rate by claim type (12 months, non-rejected)\n", rates.to_string(index=False))
rates.to_csv(HERE / "discovery_chart_r1_rates.csv", index=False)
