"""Runs the check set through the app and compares with the expected answers in check_set.csv.

  python checks/run_checks.py            claims run for real; emails use the gold reading of each email (tests the code, no key needed)
  python checks/run_checks.py --live     emails are read by the real model (needs OPENROUTER_API_KEY in .env): tests the model reading too

Writes checks/results.csv and prints PASS/FAIL per record. A record passes when the route, the set of flagged rules and the
amount at issue (within 0.01) all match.
"""
import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from agent import pipeline as P  # noqa: E402

live = "--live" in sys.argv
gold = json.loads((HERE / "gold_reads.json").read_text())


def offline_model(system, user):
    if "read one email" in system:
        for eid, g in gold.items():
            if eid in offline_model.current:
                return json.dumps(g)
    raise RuntimeError("offline")        # explanation falls back to the template


if live:
    from agent.llm import make_model_call
    model = make_model_call()
else:
    model = offline_model

exp = pd.read_csv(HERE / "check_set.csv", keep_default_na=False)
res, cache = [], {}
for r in exp.itertuples():
    offline_model.current = r.input
    if r.input not in cache:
        cache[r.input] = P.run_sequential({"input": r.input}, model)
    answers = cache[r.input]
    a = answers[r.line - 1] if len(answers) >= r.line else None
    if a is None:
        got = dict(route="(no answer)", flags="", amount=0.0)
    else:
        flags = sorted(c["rule"] for c in a["checks"] if c["status"] in ("flag", "needs_person"))
        got = dict(route=a["recommendation"], flags=" ".join(flags), amount=a["amount_at_issue_inr"])
    want_flags = " ".join(sorted(str(r.expected_flags).split()))
    # for a claim that is not found or an email that cannot be read, no checks run, so no flags are expected
    ok = got["route"] == r.expected_route and got["flags"] == want_flags and abs(got["amount"] - float(r.expected_amount_inr)) <= 0.01
    res.append(dict(case_id=r.case_id, expected_route=r.expected_route, got_route=got["route"], expected_flags=want_flags, got_flags=got["flags"],
                    expected_amount=r.expected_amount_inr, got_amount=got["amount"], result="PASS" if ok else "FAIL"))
out = pd.DataFrame(res)
out.to_csv(HERE / ("results_live.csv" if live else "results.csv"), index=False)
print(out.to_string(index=False))
print(f"\n{(out.result == 'PASS').sum()} of {len(out)} records match the expected answers" + (" (live model)" if live else " (gold email reading)"))
sys.exit(0 if (out.result == "PASS").all() else 1)
