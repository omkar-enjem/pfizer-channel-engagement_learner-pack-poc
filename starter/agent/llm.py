"""The one place that knows which model and provider we use (same pattern as LangChain 2)."""
import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = os.getenv("MODEL", "openai/gpt-4o-mini")


def get_llm(temperature: float = 0) -> ChatOpenAI:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is not set. Locally: put it in .env. On Vercel: add it under Settings, Environment Variables.")
    return ChatOpenAI(model=DEFAULT_MODEL, api_key=api_key, base_url=OPENROUTER_BASE_URL, temperature=temperature)
