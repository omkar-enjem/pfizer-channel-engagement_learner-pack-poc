# notebooks/

Run in order. Raw data in `data-pack/data/` is **read-only**: never open it in Excel and never save over it.
(If a file gets touched: `git restore data-pack/data/<file>.csv`.)

| Order | File | What it does | Writes |
|---|---|---|---|
| 1 | `step3_evidence.ipynb` | E0 checks the raw files are intact, then reproduces every number quoted during the Step 3 data checks | nothing |
| 2 | `step3_clean.ipynb` | Loads the 7 CSVs as text, standardises dates/codes/numbers, drops exact duplicates, flags conflicts, validates | `data-clean/*.csv` (with `src_row` = line number in the raw file), and the audit trail below (including `cleaning_log.csv`) |
| 3 | `step3_links.ipynb` | 3.4: orphan checks (every code exists in its master), values stored twice agree, every expiry claim traced to a sales line, explains the 971 claims on older batches. Run after `step3_clean.ipynb` | `data-clean/audit/links/` (`link_check_summary.csv`, `claims_traceability.csv`, `claims_traceability_summary.csv`) |
| 4 | `step3_dictionary.ipynb` | 3.5: data dictionary (every column: meaning, source page, documented / listed / added) and data-quality log (every problem, action, basis). Run after `step3_links.ipynb` | `notes/data_dictionary.md`, `notes/data_quality_log.md`, `data-clean/audit/data_dictionary.csv`, `data-clean/audit/data_quality_log.csv` |
| 5 | `step3_qbr.ipynb` | 3.6: reproduces the Finance QBR scorecard (primary, FOC, claims, fill rate, turnaround, CFA inventory) from the clean data and shows MATCH / CLOSE / DIFFERS for each quarter. Run after `step3_clean.ipynb` | `data-clean/audit/qbr_reconciliation.csv`, `notes/qbr_reconciliation.md` |
| 6 | `step4_rules.ipynb` | 4.1: tests the client's rules R1 to R13 against the clean data: breach count, rupees at issue, rows to check by hand (R13 not testable). Reads `pilot/data/` through the loader. Needs `python -m agent.data --sync ..\data-clean` first | `data-clean/audit/rules/rules_summary.csv` and one CSV per rule |
| 7 | `step4_beliefs.ipynb` | 4.2: tests what client staff said (beliefs B1 to B9) and gives a verdict for each with the number behind it. Same needs as row 6 | `data-clean/audit/beliefs/beliefs_summary.csv` and one CSV per belief |
| 8 | `step4_sizing.ipynb` | 4.3: gives each finding a rupee size (last 12 months and whole window), a kind, a confidence and a proposed owner; ranks inside each kind and never adds across kinds. Needs `step4_rules.ipynb` run first | `data-clean/audit/sizing/sizing_table.csv` |
| 9 | `step4_recovery.ipynb` | 4.4: the CFO ask. Puts every claim of the last 12 months in one of three groups (breaks a rule / linked to a scheme batch / the rest), then shows what can be stopped, reclaimed, prevented or avoided, and the questions the client must answer first. Needs `step4_rules.ipynb` run first | `data-clean/audit/recovery/groups.csv`, `levers.csv` |

Setup: `pip install -r notebooks/requirements.txt` (pandas, matplotlib, xlsxwriter, ipykernel), then open in VS Code with a Python kernel.
Run cells top to bottom (Shift+Enter). Each section ends with a **Check** line saying what you should see.

Not committed on purpose: `data-clean/` is generated. Add `data-clean/` to `.gitignore` if you prefer.

## Audit trail (`data-clean/audit/`, written by `step3_clean.ipynb`)

| File | Proves |
|---|---|
| `cleaning_log.csv` | the rules applied: what, why, how many rows. The notebook asserts it agrees with the dropped-row files |
| `audit_summary.csv` | per file: rows in, dropped, out, cells changed, rows flagged. The notebook asserts `rows_in - dropped = rows_out` |
| `dropped_rows_<file>.csv` | every deleted row in full, plus `duplicate_of_src_row` (the kept row it copies) |
| `changed_cells.csv` | every altered cell: file, `src_row`, key, column, old value, new value, rule. Dates are listed only when the text really changed (dd-Mon-yyyy -> yyyy-mm-dd). dd-mm-yyyy and already-ISO dates keep the same value and are not listed |
| `flagged_rows.csv` | rows kept but marked: cancelled line, missing order qty, quantity conflict, stock-out marker, missing invoice ref |

`src_row` is the line number in the raw CSV (header = line 1): open the raw file in VS Code, press Ctrl+G, and type it to see the original row.

## Visual proof (written by `step3_clean.ipynb` on every run)

| Output | How to use it |
|---|---|
| Charts inside the notebook (section 3.3f) | rows in/out, cells changed by rule, money check, flagged rows, `scheme_code` pies before/after |
| Row inspector `show_row(file, src_row)` | type any row number to see the raw row next to the clean row (or the dropped duplicate and the row it copies) |
| `data-clean/audit/verification_report.html` | opens in your browser automatically (`OPEN_REPORT = False` to stop that); one-page proof you can read or print to PDF |
| `data-clean/audit/audit_proof.xlsx` | Excel: sheets Summary, ByRule, SchemeBefore, SchemeAfter, RuleLog, Dropped_*, Flagged, ChangedCells, with native charts on the first four |
