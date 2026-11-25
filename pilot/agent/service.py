"""What the API does, as plain functions (no web framework), so it can be tested anywhere."""
from __future__ import annotations

from agent import pipeline as P
from agent.data import load

MAX_INPUT_CHARS = 4000


class BadInput(ValueError):
    pass


def check(text, graph, stockist_code=None, received_date=None) -> dict:
    text = (text or "").strip()
    if not text:
        raise BadInput("Type a claim number, an email id, or paste the email text")
    if len(text) > MAX_INPUT_CHARS:
        raise BadInput(f"Input is longer than {MAX_INPUT_CHARS} characters")
    from agent.graph import run_all      # imported here so validation and listings work without LangGraph
    kind = P.classify_input(text)
    results = run_all(text, stockist_code=(stockist_code or "").strip().upper() or None,
                      received_date=(received_date or "").strip() or None, graph=graph)
    return {"input_kind": kind, "results": results}


def emails() -> list[dict]:
    df = load("claim_emails").sort_values("email_id")
    return [{"email_id": r.email_id, "from": r.from_name, "subject": r.subject} for r in df.itertuples()]


def health() -> dict:
    return {"claims": len(load("expiry_claims")), "emails": len(load("claim_emails"))}
