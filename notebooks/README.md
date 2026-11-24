# notebooks/

Run in order. Raw data in `data-pack/data/` is **read-only**: never open it in Excel and never save over it.
(If a file gets touched: `git restore data-pack/data/<file>.csv`.)

| Order | File | What it does | Writes |
|---|---|---|---|
| 1 | `step3_evidence.ipynb` | E0 checks the raw files are intact, then reproduces every number quoted during the Step 3 data checks | nothing |
| 2 | `step3_clean.ipynb` | Loads the 7 CSVs as text, standardises dates/codes/numbers, drops exact duplicates, flags conflicts, validates | `data-clean/*.csv`, `data-clean/cleaning_log.csv`, `data-clean/dropped_duplicates_*.csv` |

Setup: `pip install -r notebooks/requirements.txt`, then open in VS Code with a Python kernel.
Run cells top to bottom (Shift+Enter). Each section ends with a **Check** line saying what you should see.

Not committed on purpose: `data-clean/` is generated. Add `data-clean/` to `.gitignore` if you prefer.
Next: `step3_links.ipynb` (3.4: do codes in one file exist in the others?), then the data dictionary and data-quality log (3.5).
