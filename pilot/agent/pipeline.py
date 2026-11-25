"""The steps of the workflow as plain functions: state in, update out. graph.py wires them into LangGraph.

Only two steps use a model (read_email, explain). Everything that decides is Python.
`model_call(system, user) -> text` is passed in, so tests can use a fake one.
"""
from __future__ import annotations

import json
import re

import pandas as pd

import config as C
from agent import check as K
from agent import prompts
from agent import rules as R
from agent import tools as T
from agent.data import load

INJECTION = re.compile(r"system note|ignore (all |the )?(previous|above)|ai assistant|pre-?approved|skip (all )?checks|approve the full", re.I)
NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _terminal(reason: str, route: str = C.NEEDS_PERSON, **extra) -> dict:
    return {"decision": {"route": route, "reasons": [reason], "amount_at_issue_inr": 0.0, "informational": []}, **extra}


def classify_input(text: str) -> str:
    t = (text or "").strip().upper()
    if re.fullmatch(r"CLM-\d{4}-\d{5}", t):
        return "claim_no"
    if re.fullmatch(r"EML-\d{3}", t):
        return "email_id"
    return "email_text"


# ---------------------------------------------------------------- read_email (model)
def load_email(email_id: str):
    df = load("claim_emails")
    m = df[df.email_id == email_id.strip().upper()]
    return None if m.empty else {k: T.py(v) for k, v in m.iloc[0].items()}


def parse_lines(raw: str) -> list[dict]:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.M).strip()
    data = json.loads(raw)
    lines = data["lines"]
    if not isinstance(lines, list) or not lines:
        raise ValueError("no lines")
    out = []
    for ln in lines:
        if not isinstance(ln, dict):
            raise ValueError("bad line")
        intent = ln.get("intent")
        if intent not in ("expiry_claim", "status_query", "other"):
            raise ValueError("bad intent")
        out.append({k: ln.get(k) for k in ("intent", "product", "batch_no", "expiry_text", "qty", "unit", "strips_per_box", "invoice_ref", "claim_no")})
    return out


def read_email(state: dict, model_call) -> dict:
    """Input is an email id or pasted text. One model call, one retry, then a person."""
    kind = classify_input(state["input"])
    update: dict = {"kind": kind, "calls": state.get("calls", 0)}
    text, stockist, received, src = state["input"], state.get("stockist_code"), state.get("received_date"), None
    if kind == "email_id":
        row = load_email(state["input"])
        if row is None:
            return {**update, **_terminal(f"Email {state['input']} is not in claim_emails.csv")}
        text = f"Subject: {row['subject']}\n\n{row['body']}"
        stockist, received = row["stockist_code_by_mailbox_rule"], str(row["received_date"])[:10]
        src = {"fact": "The email", "file": "claim_emails.csv", "rows": [row["src_row"]],
               "values": {"email_id": row["email_id"], "received_date": received, "stockist_code": stockist, "subject": row["subject"]}}
        update["email_from"] = row["from_name"]
    update.update(stockist_code=stockist, received_date=received, source_evidence=src, email_text=text)
    notes = []
    if INJECTION.search(text):
        notes.append("The email contains instructions addressed to the assistant. They were ignored; the checks ran as normal.")
    last = None
    for _ in range(2):
        update["calls"] += 1
        try:
            update["cases"] = parse_lines(model_call(prompts.READ_EMAIL, text))
            update["index"] = 0
            update["notes"] = notes
            return update
        except Exception as e:   # model down, slow, or answer not valid JSON
            last = e
    return {**update, "notes": notes, **_terminal(f"The email could not be read automatically ({type(last).__name__}). A person should open it")}


# ---------------------------------------------------------------- fetch (Python)
def fetch(state: dict) -> dict:
    kind = state.get("kind") or classify_input(state["input"])
    if kind == "claim_no":
        claim = T.find_claim(state["input"])
        if claim is None:
            return _terminal(f"Claim {state['input'].strip().upper()} is not in the claims file", kind=kind)
        return {"kind": kind, "claim": claim, "facts": K.gather(claim)}
    cases, i = state["cases"], state.get("index", 0)
    case = cases[i]
    base = {"case": case, "case_count": len(cases)}
    if case["intent"] == "status_query":
        cn = (case.get("claim_no") or "").strip().upper()
        if not cn:
            return {**base, **_terminal("A status query with no claim number. A person should look up the claim by stockist and batch")}
        claim = T.find_claim(cn)
        if claim is None:
            return {**base, **_terminal(f"Claim {cn} is not in the claims file")}
        return {**base, "claim": claim, "facts": K.gather(claim)}
    if case["intent"] != "expiry_claim":
        return {**base, **_terminal("This email is not an expiry or breakage claim. Send it to the right team")}
    claim, why = build_email_claim(case, state.get("stockist_code"), state.get("received_date"))
    if claim is None:
        return {**base, **_terminal(why)}
    return {**base, "claim": claim, "facts": K.gather(claim, state.get("source_evidence"), same_email_lines(cases, i, claim))}


def same_email_lines(cases: list, i: int, claim: dict) -> list:
    """Earlier lines of this same email for the same batch, counted like earlier claims (the register cannot know about them)."""
    out = []
    for n, c in enumerate(cases[:i], start=1):
        same = (c.get("intent") == "expiry_claim" and (c.get("batch_no") or "").strip().upper() == claim["batch_no"]
                and isinstance(c.get("qty"), (int, float)))
        if same:
            q = float(c["qty"]) * (float(c.get("strips_per_box") or 1) if (c.get("unit") or "strips").lower() in ("boxes", "cartons") else 1)
            out.append({"claim_no": f"line {n} of this email", "qty_claimed": int(q), "status": "New", "src_row": None})
    return out


def build_email_claim(case: dict, stockist_code, received_date):
    """A claim record from one email line. Returns (claim, None) or (None, reason a person must resolve)."""
    stockist_code = stockist_code if isinstance(stockist_code, str) and stockist_code.startswith("STK") else None
    if not stockist_code:
        return None, "The sender is not matched to a stockist (no stockist code). A person should confirm who sent it"
    if T.stockist(stockist_code) is None:
        return None, f"Stockist {stockist_code} is not in stockist_master.csv"
    batch_no = (case.get("batch_no") or "").strip().upper()
    if not batch_no:
        return None, "No batch number in the email. A person should ask the stockist for it"
    bm = T.batch(batch_no)
    if bm is None:
        return None, f"Batch {batch_no} is not in batch_master.csv. Check the batch number with the stockist"
    qty = case.get("qty")
    if not isinstance(qty, (int, float)) or qty <= 0:
        return None, "No usable quantity in the email"
    qty = float(qty)
    unit = (case.get("unit") or "strips").lower()
    if unit in ("boxes", "cartons"):
        spb = case.get("strips_per_box")
        if not isinstance(spb, (int, float)) or spb <= 0:
            return None, f"Quantity is in {unit} but the email does not say how many strips per box"
        qty *= float(spb)
    if qty != int(qty):
        return None, "Quantity is not a whole number of strips"
    ref = (case.get("invoice_ref") or "").strip().upper() or None
    if ref:
        ref = re.sub(r"^INV-(\w+)-(\d+)-(\d+)$", r"INV/\1/\2/\3", ref)    # same invoice written with hyphens
    received = pd.Timestamp(received_date) if received_date else None
    if received is None or pd.isna(received):
        return None, "No received date for the email"
    expiry = pd.Timestamp(bm["expiry_date"])
    sk = T.sku(bm["sku_code"])
    claim = {"src_row": None, "claim_no": None, "claim_date": received, "stockist_code": stockist_code, "cnf_code": None,
             "sku_code": bm["sku_code"], "batch_no": batch_no, "expiry_date_as_claimed": expiry, "qty_claimed": int(qty),
             "claim_value_inr": None, "claim_value_derived_inr": round(int(qty) * sk["pts_inr"], 2),
             "claim_type": C.NEAR_EXPIRY if expiry >= received else C.EXPIRED, "original_invoice_ref": ref, "status": "New",
             "credit_note_no": None, "credit_note_date": None, "credit_value_inr": None, "remarks": None}
    return claim, None


# ---------------------------------------------------------------- the seven checks and the route (Python)
def run_check(rule: str, state: dict) -> dict:
    f = state.get("facts")
    if f is None or rule not in K.rules_for(f):
        return {}
    return {"checks": [K.run_rule(rule, f)]}


def route(state: dict) -> dict:
    if state.get("decision"):          # already decided: not found, blank batch, model failed...
        return {}
    f = state["facts"]
    order = {r: i for i, r in enumerate(K.ALL_RULES)}
    checks = sorted(state["checks"], key=lambda c: order[c.rule])
    return {"decision": R.decide(checks, f["value"]), "evidence": K.evidence_for(f),
            "claim_out": K.claim_out(f["claim"], f["value"])}


# ---------------------------------------------------------------- explain (model, then guard)
def facts_for_model(state: dict) -> dict:
    d = state["decision"]
    return {"recommendation": d["route"], "reasons": d["reasons"], "amount_at_issue_inr": d["amount_at_issue_inr"],
            "informational": d.get("informational", []),
            "checks": [{"rule": c.rule, "status": c.status, "summary": c.summary} for c in state.get("checks", [])],
            "claim": {k: v for k, v in (state.get("claim_out") or {}).items() if k in ("claim_no", "claim_date", "claim_type", "stockist_code", "batch_no", "qty_claimed", "claim_value_used_inr")}}


def numbers_in(text: str) -> set:
    return {n.replace(",", "").rstrip("0").rstrip(".") if "." in n else n.replace(",", "") for n in NUM.findall(text)}


def explanation_ok(text: str, facts: dict) -> bool:
    return bool(text.strip()) and numbers_in(text) <= numbers_in(json.dumps(facts, default=str))


LABEL = {C.CREDIT_FOR_REVIEW: "Credit for review", C.HOLD: "Hold", C.NEEDS_PERSON: "Needs a person"}


def template_text(state: dict) -> str:
    d = state["decision"]
    s = f"{LABEL[d['route']]}. " + " ".join(r.rstrip(".") + "." for r in d["reasons"])
    if d["amount_at_issue_inr"]:
        s += f" Amount at issue: Rs {d['amount_at_issue_inr']:,.2f}."
    return s


def explain(state: dict, model_call) -> dict:
    facts = facts_for_model(state)
    calls = state.get("calls", 0)
    if calls < 2:
        try:
            text = model_call(prompts.EXPLAIN, json.dumps(facts, default=str, indent=1)).strip()
            if explanation_ok(text, facts):
                return {"explanation": text, "explanation_source": "model", "calls": calls + 1}
        except Exception:
            pass
        calls += 1
    return {"explanation": template_text(state), "explanation_source": "template", "calls": calls}


# ---------------------------------------------------------------- final answer
def result(state: dict) -> dict:
    d = state["decision"]
    return {"input": state["input"], "recommendation": d["route"], "label": LABEL[d["route"]], "reasons": d["reasons"],
            "amount_at_issue_inr": d["amount_at_issue_inr"], "informational": d.get("informational", []),
            "explanation": state.get("explanation"), "explanation_source": state.get("explanation_source"),
            "checks": [c.as_dict() for c in sorted(state.get("checks", []), key=lambda c: K.ALL_RULES.index(c.rule))], "evidence": state.get("evidence", []),
            "claim": state.get("claim_out"), "notes": state.get("notes", []), "model_calls": state.get("calls", 0),
            "case_number": state.get("index", 0) + 1, "case_count": state.get("case_count", 1)}


def run_sequential(state: dict, model_call) -> list[dict]:
    """The same steps in a plain loop, one answer per claim line. Used by tests, and as a check that the LangGraph wiring agrees."""
    state = dict(state)
    if classify_input(state["input"]) != "claim_no" and "cases" not in state:
        state.update(read_email(state, model_call))
    n = len(state["cases"]) if state.get("cases") else 1
    out = []
    for i in range(n):
        s = dict(state)
        s["index"] = i
        if i:
            s["calls"] = 0
        if not s.get("decision"):
            s.update(fetch(s))
        if not s.get("decision"):
            s["checks"] = []
            for r in K.ALL_RULES:
                s["checks"] += run_check(r, s).get("checks", [])
        s.update(route(s))
        s.update(explain(s, model_call))
        out.append(result(s))
    return out
