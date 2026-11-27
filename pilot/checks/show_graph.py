"""Print the compiled LangGraph workflow as Mermaid text and save it to docs/graph.mmd (same as `python -m agent.graph`).

  python checks/show_graph.py

No API key and no network. Paste the text into https://mermaid.live to see the diagram.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from agent.graph import draw  # noqa: E402

out = ROOT / "docs" / "graph.mmd"
print(draw(str(out)))
print(f"\nSaved to {out}. Paste it into https://mermaid.live to see the diagram.")
