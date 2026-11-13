"""A minimal LangGraph tool loop: the same shape as LangGraph 3, wired for a web request.

This is a skeleton to prove your deployment works end to end. Replace it with your
own design. Keep the rules in code and give the model only the judgment calls.
"""
from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from agent.llm import get_llm
from agent.tools import TOOLS

MAX_TRIPS = 4
SYSTEM = (
    "You answer questions about Pfizer Limited's General Medicines trade channel for an internal user. "
    "Use the tools for every fact. If a tool returns found=false, say so. Never invent a batch, date or number."
)


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    trips: int


def call_model(state: State) -> dict:
    llm = get_llm().bind_tools(TOOLS)
    reply = llm.invoke([SystemMessage(SYSTEM), *state["messages"]])
    return {"messages": [reply], "trips": state.get("trips", 0) + 1}


def run_tools(state: State) -> dict:
    by_name = {t.name: t for t in TOOLS}
    out = []
    for call in state["messages"][-1].tool_calls:
        result = by_name[call["name"]].invoke(call["args"])
        out.append(ToolMessage(content=str(result), tool_call_id=call["id"], name=call["name"]))
    return {"messages": out}


def route(state: State) -> str:
    last = state["messages"][-1]
    if getattr(last, "tool_calls", None) and state["trips"] < MAX_TRIPS:
        return "tools"
    return END


builder = StateGraph(State)
builder.add_node("model", call_model)
builder.add_node("tools", run_tools)
builder.add_edge(START, "model")
builder.add_conditional_edges("model", route, {"tools": "tools", END: END})
builder.add_edge("tools", "model")
graph = builder.compile()


def run_question(question: str) -> dict:
    final = graph.invoke({"messages": [HumanMessage(question)], "trips": 0})
    evidence = [m.content for m in final["messages"] if isinstance(m, ToolMessage)]
    return {"answer": final["messages"][-1].content, "evidence": evidence, "model_calls": final["trips"]}
