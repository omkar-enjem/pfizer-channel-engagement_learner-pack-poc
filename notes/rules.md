# Rules register (Step 2)

Every rule with a number in it, from the client documents.  
**Verification process:** For each rule, cross-check the details against the cited page in the source document. After verification, update the "Verified" column with the date and your initials, or note any corrections made.  
Refer to the [verification checklist](./verification-checklist.md) for step-by-step guidance.

Data tables: EC = `expiry_claims`, PS = `primary_sales`, SNAP = `cnf_stock_snapshot`.

| # | Rule | Source | Test in data | Verified |
|---|---|---|---|---|
| R1 | Claim windows: near expiry from 90 days before expiry to expiry date; expired from expiry date to 90 days after; breakage and short supply within 7 days of invoice | `02` p3 §5.2 | EC: `claim_date` vs `expiry_date_as_claimed`, `claim_type` | ✓ 23 Nov  |
| R2 | Original invoice reference required; otherwise Area Manager written approval | `02` p3 §5.3-5.4 | EC: blank `original_invoice_ref`, `remarks` | ✓ 23 Nov |
| R3 | Quantity claimed for a batch must not exceed packs invoiced to that stockist for that batch, free packs included | `02` p3 §5.5 | EC `qty_claimed` vs PS `invoiced_qty` + `free_qty` by stockist and batch |✓ 23 Nov |
| R4 | No earlier claim on the same stockist and batch | `02` p4 §5.6; `03` p3 §2.6 | EC: repeated `stockist_code` + `batch_no` | ✓ 23 Nov |
| R5 | Claims valued at the PTS in force on the claim date | `02` p4 §5.7 | EC `claim_value_inr` vs `qty_claimed` x `pts_inr`; `credit_value_inr` | ✓ 23 Nov |
| R6 | Verification within 10 working days; credit note within 30 days of receipt of claim | `02` p4 §5.6 | EC: `claim_date` to `credit_note_date`, `status` | ✓ 23 Nov |
| R7 | Remaining shelf life at least 60% at invoice; no dispatch with under 60 days to expiry | `02` p4 §7.1; `03` p3 §2.3 | PS `invoice_date` vs batch `expiry_date` and SKU `shelf_life_months` |✓ 23 Nov  |
| R8 | Free goods at PTS must not exceed 3% of quarter primary; above that needs CFO approval | `02` p2 §4.3-4.4 | PS: `free_qty` x `pts_inr` by quarter |✓ 23 Nov  |
| R9 | Quarter-end scheme valid 22nd to month-end of the quarter's last month; minimum order 1.5x the stockist's 3-month average for the SKU | `02` p5 Annex B; `02` p2 §4.2 | PS: `scheme_code` lines, dates, quantities | ✓ 23 Nov |
| R10 | C&F topped up to 2 months of allocated volume; one shipment at most 1.2 months | `03` p3 §2.2 | SNAP `qty_on_hand_packs` vs `avg_monthly_outward_packs` | ✓ 23 Nov |
| R11 | Short supply: invoice what is available, cancel the balance, no back orders | `03` p3 §2.4 | PS **per order line** (`invoice_no` + `sku_code`): sum of `invoiced_qty` across batch rows vs `ordered_qty`, which sits on the first row only (`01` p3 §5.4). Never compare row by row | ✓ 23 Nov; test corrected 24 Nov |
| R12 | Claim number format CLM-yymm-nnnnn | `03` p3 §2.6 | EC `claim_no` format; yymm vs `claim_date` |✓ 23 Nov  |
| R13 | No scheme to a stockist holding more than 2.5 months of average secondary | `02` p3 §4.5 | NOT TESTABLE: no secondary data (`01` p2 §3) |✓ 23 Nov  |

## Notes
- R13 is untestable. Record that as a finding, not a gap in the analysis.
- R5 valuation: `01` p3 §5.1 says all valuation uses the `sku_master` PTS/MRP, and in the data `claim_value_inr` = `qty_claimed` x `sku_master.pts_inr` on all 4,368 claims that have a value (24 Nov). The extract holds one price per SKU, so "PTS on the claim date" (`02` §5.7) cannot be tested separately. Record that as a limit.
- R11 and blank `ordered_qty`: a blank is a later row of a split order line (`01` p3 §5.4), not missing data. Real order-line result: 74,133 full, 10,425 short, 2,628 not supplied of 87,186.
