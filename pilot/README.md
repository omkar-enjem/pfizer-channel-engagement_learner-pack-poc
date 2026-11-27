# Project Sankalp pilot: claim-intake check

Read-only pilot for the Controller (Neha Bansal). Enter a claim number (for example `CLM-2608-04515`), a sample email id
(`EML-014`) or paste an email. It returns **credit for review**, **hold** or **needs a person**, the reasons, the amount at issue,
the result of each check with its policy clause, and the evidence with file and row. It never writes to the ERP.

**Live:** https://pfizer-channel-engagement-learner-p.vercel.app
Health check: `/api/health`.

Tested on a device that had not been used for this project: 25 Nov 2026, a phone on mobile data. The page opened with no sign-in and
`CLM-2608-04515` returned **hold** (claim filed after expiry; probable duplicate). Vercel Deployment Protection stays on for preview URLs;
the production domain is public.

## How it works

```
input -> read_email (model) -> fetch -> R1 R2 R3 R4 R5 R6 R12 (code, parallel) -> route (code) -> explain (model) -> answer
```
Code decides; the model only reads an email into fields and words the explanation from verified facts. See `AGENTS.md` and the architecture note.

To see the compiled LangGraph as a flow diagram, run `python -m agent.graph` from this folder. It prints Mermaid text (also saved to
`docs/graph.mmd`); paste it into https://mermaid.live. No key needed.

| Rule | What it checks | Source |
|---|---|---|
| R1 | Claim filed inside the window (near expiry: 90 days before expiry up to expiry; expired: up to 90 days after; breakage and short supply: 7 days from invoice) | 02 p3 s5.2 |
| R2 | Invoice reference quoted and found in the sales file, or Area Manager approval in the remarks | 02 p3 s5.3-5.4 |
| R3 | Quantity within packs invoiced plus free, counting earlier non-rejected claims | 02 p3 s5.5 |
| R4 | No earlier non-rejected claim for the same quantity on this stockist and batch (probable duplicate) | 02 p4 s5.6, 03 p3 s2.6 |
| R5 | Value equals quantity x PTS (informational) | 02 p4 s5.7 |
| R6 | Credit note within 30 days (informational) | 02 p4 s5.6 |
| R12 | Claim number month matches the claim date | 03 p3 s2.6 |

R1 to R4 can put a claim on hold; R5 and R6 inform. A claim that cannot be traced goes to a person, never to a guess.

## Layout
```
app.py                 API routes only (/api/check, /api/emails, /api/health)
agent/rules.py         the rules, plain Python      config.py   every policy number with its clause
agent/check.py         gathers records and evidence tools.py    lookups, each answer carries file and row
agent/pipeline.py      the workflow steps           graph.py    the LangGraph wiring
agent/llm.py           the model provider (OpenRouter), prompts.py the two prompts
public/                one-screen UI (plain HTML, CSS, JS)
data/                  the seven clean CSVs (read-only)
checks/                18-record check set, independent derivation, runner
tests/                 110 tests
```

## Run it
```
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env          # add OPENROUTER_API_KEY; MODEL defaults to openai/gpt-4o-mini
python -m pytest -q             # 110 passed
uvicorn app:app --reload
```
Without a key, claim numbers still get all checks with a template explanation; emails go to "needs a person".

## Accuracy
- **Rules vs the data:** `tests/test_reconcile.py` runs every rule over all 4,503 claims and matches the figures in the validated notebooks.
- **Check set:** `checks/check_set.csv` has 18 records (10 claims, 8 email lines). `checks/derive_expected.py` works out each expected
  answer from the source rows without using `agent/rules.py`; the Source column names the file and row to open. Results:
  `python checks/run_checks.py` gives **18 of 18** with a fixed reading of the emails, and `--live` gives **18 of 18** with the real model
  reading the emails (run 25 Nov 2026, one run).
- **Batch run:** `python checks/batch_12m.py` puts the 2,294 non-rejected claims of 1 Oct 2025 to 30 Sep 2026 through the rules (no model, no
  network) and writes `checks/batch_12m_results.csv`: 1,589 credit for review, 626 hold, 79 needs a person; 336 claims break R1, R3 or R4
  (value 0.905 crore, 265 already credited). Claim value is quantity x PTS where none is recorded. Discovery's 5.44 crore uses the credit
  note value for credited claims, so it differs from this run's 5.47 crore by basis, not by claims.
- **Nothing invented:** a number in the model's explanation that is not in the evidence is dropped and a fixed template is used.

## Known limits
- 768 older claims quote invoices that are not in the sales extract (it starts Apr 2024), so they go to "needs a person" (R2).
- R5 cannot test "PTS on the claim date": the pack has one price per SKU.
- R2 looks for approval words in the remarks only; an approval kept elsewhere is not seen.
- 84 claims whose claim number and date disagree go to "needs a person" (R12).
- The email check is 8 lines from the sample mailbox, one live run; it is evidence, not a guarantee for every email.
- Forecast accuracy cannot be tested with this data (no forecast snapshots, no secondary sales).
- Cost, token counts and the 30 s timeout are planning assumptions from the architecture note, not measured on the live deployment.
