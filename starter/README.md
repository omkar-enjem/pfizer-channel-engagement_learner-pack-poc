# Project Sankalp pilot: starter

An optional skeleton for the recommended path. It already deploys to Vercel: a FastAPI backend, a LangGraph tool loop and a
plain HTML page. It proves your pipeline works on day one. Replace the graph, the tools and
the page with your own design.

```
app.py            FastAPI entrypoint (Vercel looks for `app` here)
agent/llm.py      the only file that knows the model provider (OpenRouter)
agent/tools.py    tools that read data/; exact facts come from here
agent/graph.py    the LangGraph graph; replace it with yours
data/             put the four CSVs from the data pack here
public/           index.html, app.js, style.css: the frontend
tests/            run with pytest; no API key needed
AGENTS.md         instructions for your AI coding agent
```

## Run it on your laptop

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt uvicorn pytest httpx
cp .env.example .env               # then put your OpenRouter key in .env
pytest -q
uvicorn app:app --reload
```

Open http://127.0.0.1:8000 and ask about a batch number from `data/batch_master.csv`.

## Deploy

Follow the step-by-step section in the Build and Deploy Guide. In short: push to GitHub,
import the repository in Vercel, add `OPENROUTER_API_KEY` as an environment variable, deploy.
