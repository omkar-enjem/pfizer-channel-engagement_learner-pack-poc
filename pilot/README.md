# pilot/

The app root for Project Sankalp (built in Step 6 from `starter/`). So far it holds the data loader.

```
agent/data.py        loads the 7 CLEAN tables with real types; checks row counts; never changes a value
tests/test_data.py   8 tests on the loader and on numbers that must not move
data/                the seven clean CSVs (generated, see below)
```

## Set up (from this folder)

```bash
pip install -r requirements.txt
python -m agent.data --sync ../data-clean     # copies and checks the clean CSVs into data/
python -m agent.data                          # prints rows per table
pytest -q                                     # expect: 8 passed
```

Run `notebooks/step3_clean.ipynb` first so `../data-clean/` exists. Re-run the `--sync` line after every re-clean.
`data/` is committed in the final repo because Vercel reads it at run time (Build and Deploy Guide, troubleshooting: CSV not found).
