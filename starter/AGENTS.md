# Instructions for the coding agent

Read this file before every task. Keep it short and keep it true.

## What we are building
<One paragraph: the user, the job they do every week, and what this tool changes for them.>

## Architecture
<Your graph: nodes, edges, which nodes call a model and which are plain code. Paste the
diagram from your architecture note.>

## Rules
- Facts come from tools that read `data/`. The model never writes a batch number, date,
  quantity or amount that did not come from a tool result.
- Business rules (claim windows, quantity limits, thresholds) live in plain Python in
  `agent/rules.py`, each with a pytest test.
- One small change per task. Run `pytest -q` after each change. Do not touch files the task
  does not need.
- Do not add a database, a vector store, a new framework or a new folder without asking.
- The frontend stays in `public/` as plain HTML, CSS and JavaScript.
- Secrets live only in `.env` locally and in Vercel environment variables. Never commit them.

## How to run
pip install -r requirements.txt uvicorn pytest httpx
pytest -q
uvicorn app:app --reload

## Current task
<Paste the slice you are working on, with what "done" means.>
