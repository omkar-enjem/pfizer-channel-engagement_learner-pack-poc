"""The model provider, in one place. Everything else gets a plain function: model_call(system, user) -> text."""
from __future__ import annotations

import os

TIMEOUT_S = 30


def get_llm():
    from dotenv import load_dotenv
    from langchain_openai import ChatOpenAI
    load_dotenv()
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise ValueError("OPENROUTER_API_KEY is not set (put it in .env or the Vercel environment variables)")
    return ChatOpenAI(model=os.getenv("MODEL", "openai/gpt-4o-mini"), api_key=key, base_url="https://openrouter.ai/api/v1",
                      temperature=0, timeout=TIMEOUT_S, max_retries=0)


def make_model_call():
    """The model is created on first use, so a missing key only affects the two model steps (they then fall back)."""
    holder = {}

    def call(system: str, user: str) -> str:
        if "llm" not in holder:
            holder["llm"] = get_llm()
        msg = holder["llm"].invoke([("system", system), ("user", user)])
        return msg.content if isinstance(msg.content, str) else str(msg.content)
    return call
