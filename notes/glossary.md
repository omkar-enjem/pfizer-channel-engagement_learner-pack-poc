# Glossary

Terms used in the Pfizer Channel Engagement learner pack. Add terms as they come up in the client documents, data extracts and voice notes.

Page numbers are PDF page numbers (page 1 is the first page of the file). "Date read" is the date the source was checked.

| Term | Meaning | Source (file, page) | Date read |
|---|---|---|---|
| CFA | Carrying and Forwarding Agent (also written C&F or CNF). Appointed by the Company to receive, store, pick, pack, dispatch and account for its products, and to receive and process returns and claims, on the terms of the agreement. | `03_cnf_agreement_and_sop.pdf`, p. 1, clause 1.1 | 2026-11-23 |
| PTS | Price to Stockist. The Company's price to the stockist for each SKU. It is the taxable value on the tax invoice and the basis for valuing returns, credit notes and claims. | `02_trade_terms_and_returns_policy.pdf`, p. 2, section 2.3 | 2026-11-23 |
 NE returns | Near-expiry return: stock that will expire within 90 days; claimable from 90 days before expiry to the expiry date. Related types: Expired (from the expiry date to 90 days after) and BED (not expanded in the pack). Breakage in transit and short supply have a separate 7-day window from the invoice. Claims dated more than 90 days after expiry are never accepted. | `02_trade_terms_and_returns_policy.pdf`, p. 3, sections 5.1–5.2 | 2026-11-23 |
| CN | Credit Note: raised for the stockist by Commercial Finance within 30 days of receipt of the claim; it references the original supply. | `02_trade_terms_and_returns_policy.pdf`, p. 4, sections 5.6–5.7; `01_company_and_channel_overview.pdf`, p. 2 | 2026-11-23 |

| DPCO | Drugs (Prices Control) Order, 2013: India's pharmaceutical price-control regulation. Relevant paragraphs are 14, 16 and 20. | `01_company_and_channel_overview.pdf`, p. 2; `02_trade_terms_and_returns_policy.pdf`, pp. 1 and 4 | 2026-11-23 |
| NLEM | National List of Essential Medicines (2022 edition). | `01_company_and_channel_overview.pdf`, p. 2; `02_trade_terms_and_returns_policy.pdf`, p. 1 | 2026-11-23 |
| NPPA | National Pharmaceutical Pricing Authority. Issues the annual WPI-linked ceiling price notification (March 2026). | `01_company_and_channel_overview.pdf`, p. 2; `02_trade_terms_and_returns_policy.pdf`, pp. 1 and 4; `05_inbox_export.pdf`, p. 3 | 2026-11-23 |
| WPI | Wholesale Price Index. | `02_trade_terms_and_returns_policy.pdf`, p. 4; `01_company_and_channel_overview.pdf`, p. 2 | 2026-11-23 |
| SLOB | Slow-Moving and Obsolete Inventory. Observed at the Kolkata C&F, which is operating near capacity with slow-moving stock. | **Not found in the client documents** (searched all six PDFs). Confirm against the voice notes or data extracts. | 2026-11-23 |
| OTIF | On Time, In Full. | **Not found in the client documents** (searched all six PDFs). Confirm before use. | 2026-11-23 |
| Schedule H1 | Sale records are the stockist's responsibility. | `02_trade_terms_and_returns_policy.pdf`, p. 4 | 2026-11-23 |
| MIS | Management Information System. | `06_qbr_finance_and_mis_pack.pdf`, p. 1 | 2026-11-23 |
| QBR | Quarterly Business Review. | `06_qbr_finance_and_mis_pack.pdf`, p. 1 | 2026-11-23 |
| Voice note | A recording forwarded by field, CFA or office staff, stored in `data-pack/voice-notes/`. | `data-pack/voice-notes/README.md` | 2026-11-23 |
| Raw extract | One of the seven unprocessed data files in `data-pack/data/`. | `01_company_and_channel_overview.pdf`, p. 3, section 5 (data extracts) | 2026-11-23 |
| Client document | One of the six documents in `data-pack/01` to `06`. | `README.md` (learner pack), top-level file | 2026-11-23 |
| Starter | The optional skeleton app in `starter/`, used for the recommended build path. | `README.md` (learner pack), top-level file | 2026-11-23 |
| Project brief | `02_project_brief.pdf`: goal, deliverables, limits and evaluation criteria. | `README.md` (learner pack), top-level file | 2026-11-23 |

## CFO statement

The CFO is concerned about two key metrics. Expiry returns as a percentage of primary sales in General Medicines (GM) were below 1% two years ago but have increased to approximately 3% in the current half-year. During the same period, the fill rate has declined, and the North region is short on SKUs that are being destroyed elsewhere.
He believes the forecasting process is inaccurate because the company is experiencing stock shortages and excess inventory simultaneously across different regions.
Having seen AI-powered demand-sensing tools used by other companies, the CFO wants to implement an AI-based forecasting solution before the Q4 scheme cycle begins in January.

Source: `01_company_and_channel_overview.pdf`, p. 1 (section 1). The CFO note is at Appendix A (p. 5) and the charter is at section 6 (p. 4). The five-quarter span is from the QBR scorecard, `06_qbr_finance_and_mis_pack.pdf`, p. 1. Date read: 2026-11-23.

## Channel Mapping

### Layer 1: goods and invoices (left to right)

Pfizer Plant/ LL Site --QA release, CoA--> CDC Bhiwandi --Monthly allocation, STN--> CFA (6) --Pfizer invoice (Primary)--> Stockists (156) --Stockist invoice (Secondary)--> Retail / sub-stockist → patient

Source: `01_company_and_channel_overview.pdf`, p. 2, section 3. The "→ patient" step is not in the pack. Date read: 2026-11-23.

### Layer 2: claims (right to left)

Stockists (156) --> CFA --> Commercial Finance --> CN (Credit Note)

Claim types: NE/expiry, breakage in transit, short supply (`01_company_and_channel_overview.pdf`, p. 2, section 3). Date read: 2026-11-23.

### Layer 3: owners

From `01_company_and_channel_overview.pdf`, p. 2, section 4. The function labels in the PDF text are misaligned with the names, so only the names and scopes are listed.

- Rohan Mehta, CFO: sponsor; returns provision; write-off approvals
- Neha Bansal, Controller: CN, claims accounting, scheme accruals
- Arjun Sethi, NSM: primary targets, trade schemes, stockist relations
- Kavita Rao, Head SC: planning, CDC, CFA replenishment, CFA contracts
- Vaishali Kapoor, Lead: national forecast, allocation plan
- Subhajit Banerjee, RDM East: CFA and transporter performance, East
- Anita Desai, Head: Project Sankalp lead

Date read: 2026-11-23.

### Layer 4: visibility

- Secondary visibility for GM is nil. There is no SSS(Secondary Sales Statement), and the DMS pilot (2023) was discontinued. AWACS gives IPM-level secondary only, not by stockist (`01_company_and_channel_overview.pdf`, p. 2, section 3).

Date read: 2026-11-23.

**Aliases:** C&F and CNF are the same as CFA. Use CFA in new writing.

**Why:** A shared vocabulary keeps the team from mixing up terms from the client documents and the voice notes.
**How to apply:** Add a row whenever a new term or acronym appears, and link to the source file and page where it is defined.
