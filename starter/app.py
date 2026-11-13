"""FastAPI entrypoint. Vercel finds the FastAPI instance named `app` in app.py.

Run locally:   uvicorn app:app --reload        then open http://127.0.0.1:8000
On Vercel:     the files in public/ are served from the CDN; /api/* reaches this app.
"""
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from agent.graph import run_question

app = FastAPI(title="Project Sankalp pilot")
ROOT = Path(__file__).resolve().parent


class Ask(BaseModel):
    question: str


@app.get("/api/health")
def health():
    """Quick check that the deployment is alive and the key is configured."""
    return {"ok": True, "model_key_set": bool(os.getenv("OPENROUTER_API_KEY"))}


@app.post("/api/ask")
def ask(body: Ask):
    """Run one question through the graph and return the answer and the evidence."""
    try:
        return run_question(body.question)
    except ValueError as err:  # missing key or bad input: say so instead of a bare 500
        return JSONResponse({"error": str(err)}, status_code=503)


@app.get("/")
def index():
    return FileResponse(ROOT / "public" / "index.html")


# On Vercel the public/ folder is served by the platform, and Vercel's docs say not to
# mount it. On your laptop nothing serves it, so mount it only when not on Vercel.
if not os.getenv("VERCEL"):
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=ROOT / "public"), name="public")
