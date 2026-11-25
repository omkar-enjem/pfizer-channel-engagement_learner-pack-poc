# Decision Log

Record each significant project decision here: what was decided, why, and what it affects. Newest entries go at the top.

| Date | Decision | Rationale | Alternatives considered | Status |
|---|---|---|---|---|
| 2026-11-25 | Pilot lives in `pilot/`; Vercel Root Directory changed from `starter` to `pilot`; function region Mumbai; Deployment Protection stays on and the production domain is used for the phone test. | The built app replaces the starter; Mumbai is closest to the users; protection is a security control and was not switched off. | Disable protection for the demo (rejected). Keep `starter` as root (rejected: no rules). | Accepted |
| 2026-11-25 | A repeat line inside one email counts as an earlier claim (R4 and R3). | EML-013 lists one claim twice and the register cannot know about it. | Check each line only against the register (missed the repeat). | Accepted |
| 2026-11-25 | R1 text now says "filed N days before/after expiry; allowed ..." and the explain prompt must keep before/after wording. | The model read "2 days from expiry" as "2 days remaining" (the claim was 2 days after expiry). The number guard checks numbers, not direction. | Trust the guard alone (rejected after the miss). | Accepted |
| 2026-11-25 | Check set of 18 records with expected answers derived independently of `agent/rules.py` (`checks/derive_expected.py`), including boundary cases (91 days) and awkward emails. | Accuracy must be shown against hand-agreed answers, not against the code itself. | Expected answers copied from app output (circular, rejected). | Accepted |
| 2026-11-24 | Code decides, the model only reads an email and words the explanation. needs_person beats hold beats credit_for_review. An explanation with a number not in the evidence is replaced by a template. Model failure never changes the recommendation. | Numbers and routes must be traceable and repeatable; models are slow or wrong sometimes. | Model tool loop deciding the route (rejected: not testable, not traceable). | Accepted |
| 2026-11-23 | Target 26 Nov EOD; build one vertical slice. | Not recorded. To be supplied. | Not recorded. | Accepted |
| 2026-11-23 | Initialised git repository in the project root. | Needed version control before building the submission. | None recorded. | Accepted |

## Entry template

Copy this block for each new decision:

```
### YYYY-MM-DD: <short decision title>
- **Context:** What problem or question prompted the decision.
- **Decision:** What was chosen.
- **Rationale:** Why it was chosen over the alternatives.
- **Alternatives considered:** Other options and why they were rejected.
- **Consequences:** What this affects, including follow-up work.
- **Status:** Proposed | Accepted | Superseded by <entry>
```
