"""The LangGraph workflow.

  input -> read_email (model; skipped for a claim number) -> fetch -> R1 R2 R3 R4 R5 R6 R12 (in parallel)
        -> route -> explain (model) -> answer

To see the compiled graph as a flow diagram (no key needed, no model is called), run from the pilot folder:
  python -m agent.graph          prints the Mermaid text and writes docs/graph.mmd; paste it into https://mermaid.live

All decisions are made by Python (pipeline.py, rules.py). The graph only gives the order and the parallel branch.
"""
from __future__ import annotations

import operator
from functools import partial
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph

import config as C
from agent import check as K
from agent import pipeline as P


class State(TypedDict, total=False):
    input: str
    stockist_code: str
    received_date: str
    kind: str
    email_text: str
    email_from: str
    source_evidence: dict
    cases: list
    index: int
    case: dict
    case_count: int
    claim: dict
    facts: dict
    checks: Annotated[list, operator.add]
    decision: dict
    evidence: list
    claim_out: dict
    notes: list
    explanation: str
    explanation_source: str
    calls: int


def _entry(state: State) -> str:
    if state.get("cases") or P.classify_input(state["input"]) == "claim_no":
        return "fetch"
    return "read_email"


def _after_read(state: State) -> str:
    return "route" if state.get("decision") else "fetch"


def _after_fetch(state: State):
    if state.get("decision"):
        return "route"
    return [f"check_{r}" for r in K.ALL_RULES]


def build(model_call=None):
    """Compile the graph. model_call(system, user) -> text; default is the OpenRouter model."""
    if model_call is None:
        from agent.llm import make_model_call
        model_call = make_model_call()
    g = StateGraph(State)
    g.add_node("read_email", partial(P.read_email, model_call=model_call))
    g.add_node("fetch", P.fetch)
    for r in K.ALL_RULES:
        g.add_node(f"check_{r}", partial(P.run_check, r))
    g.add_node("route", P.route)
    g.add_node("explain", partial(P.explain, model_call=model_call))
    g.add_conditional_edges(START, _entry, ["fetch", "read_email"])
    g.add_conditional_edges("read_email", _after_read, ["fetch", "route"])
    g.add_conditional_edges("fetch", _after_fetch, [f"check_{r}" for r in K.ALL_RULES] + ["route"])
    for r in K.ALL_RULES:
        g.add_edge(f"check_{r}", "route")
    g.add_edge("route", "explain")
    g.add_edge("explain", END)
    return g.compile()


def run_all(text: str, stockist_code: str | None = None, received_date: str | None = None, model_call=None, graph=None) -> list[dict]:
    """One input in, one answer per claim line out. A claim number or a one-line email gives a list of one."""
    graph = graph or build(model_call)
    state: dict[str, Any] = {"input": text.strip()}
    if stockist_code:
        state["stockist_code"] = stockist_code
    if received_date:
        state["received_date"] = received_date
    first = graph.invoke(state)
    out = [P.result(first)]
    for i in range(1, len(first.get("cases") or [])):
        nxt = {k: v for k, v in first.items() if k in ("input", "stockist_code", "received_date", "kind", "email_text", "email_from",
                                                       "source_evidence", "cases", "notes", "calls")}
        nxt["index"] = i
        nxt["calls"] = 0       # the one read of the email is shared; each line gets its own explain call
        out.append(P.result(graph.invoke(nxt)))
    return out


def draw(path: str | None = None) -> str:
    """The compiled graph as Mermaid text, straight from LangGraph. Optionally written to a file."""
    text = build(model_call=lambda system, user: "").get_graph().draw_mermaid()
    if path:
        from pathlib import Path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(text, encoding="utf-8")
    return text


if __name__ == "__main__":
    print(draw("docs/graph.mmd"))
