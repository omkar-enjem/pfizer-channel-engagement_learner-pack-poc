"""FastAPI entrypoint. Routes only; the work is in agent/service.py and agent/graph.py.

Run locally:   uvicorn app:app --reload        then open http://127.0.0.1:8000
On Vercel:     public/ is served by the platform and /api/* reaches this app.
"""
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from agent import service

app = FastAPI(title="Project Sankalp pilot")
ROOT = Path(__file__).resolve().parent
_GRAPH = None      # built on first use; tests put a graph with a fake model here


def get_graph():
    global _GRAPH
    if _GRAPH is None:
        from agent.graph import build
        _GRAPH = build()
    return _GRAPH


class Check(BaseModel):
    input: str
    stockist_code: str | None = None
    received_date: str | None = None


@app.get("/api/health")
def health():
    return {"ok": True, "model_key_set": bool(os.getenv("OPENROUTER_API_KEY")), **service.health()}


@app.get("/api/emails")
def emails():
    return service.emails()


@app.post("/api/check")
def check(body: Check):
    try:
        return service.check(body.input, get_graph(), body.stockist_code, body.received_date)
    except service.BadInput as err:
        return JSONResponse({"error": str(err)}, status_code=400)


@app.get("/")
def index():
    return FileResponse(ROOT / "public" / "index.html")


# On Vercel the public/ folder is served by the platform; on a laptop nothing serves it, so mount it there.
if not os.getenv("VERCEL"):
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=ROOT / "public"), name="public")
