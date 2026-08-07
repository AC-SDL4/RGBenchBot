# Uncertainty Measurement Workflow — Dataset Registry

Each experiment measures dispensing repeatability across 24 wells (4 groups × 6 replicates).
Each well is imaged 6 times; color is extracted in RGB, LAB, and HSV.
**Measurement uncertainty** = camera noise within a well. **Process uncertainty** = dispensing variability between replicate wells.

---

## Datasets

### `20260130_143830_automated_5_2_2`
- **Date:** January 30, 2026
- **Method:** Automated (machine dispensed)
- **Ink ratio:** 5:2:2 (Red:Yellow:Blue)
- **Notes:** First real hardware run. Different ink ratio from all subsequent experiments. No composition map saved; no well images saved. Partial analysis only.

---

### `20260210_150847_automated_darkest_7_1_1`
- **Date:** February 10, 2026
- **Method:** Automated
- **Ink ratio:** 7:1:1 (Red:Yellow:Blue) — switched to darkest ink concentrations
- **Notes:** Established the 7:1:1 ratio used in most subsequent runs. No composition map saved; no well images saved. Partial analysis only.

---

### `no_priming_20260213_073533_automated_darkest_more_yellow_7_1_1_group1_2_4`
- **Date:** February 13, 2026
- **Method:** Automated, **priming step skipped**
- **Ink ratio:** 7:1:1, more yellow ink
- **Notes:** The workflow normally runs 25 warm-up dispense cycles before the experiment to mechanically condition the actuator. This run skipped that step to test whether it matters. Only groups 1, 2, and 4 were completed (group 3 missing — run may have been cut short). No composition map saved; no well images saved.

---

### `20260218_141247_manual_pipett_by_hand`
- **Date:** February 18, 2026
- **Method:** **Manual pipette (human)**
- **Ink ratio:** 7:1:1
- **Notes:** Human baseline — wells were prepared by hand with a manual pipette instead of the automated dispenser. Used to compare machine vs human dispensing variability. No composition map saved; no well images saved.

---

### `BEST_20260224_123236_automated_darkest_most_yellow_7_1_1`
- **Date:** February 24, 2026
- **Method:** Automated
- **Ink ratio:** 7:1:1, most yellow ink (darkest, most saturated)
- **Groups:**
  - Group 1: Neutral (0.3 R / 0.3 Y / 0.3 B / 0.1 Water)
  - Group 2: Red-dominant (0.7 R / 0.1 Y / 0.1 B / 0.1 Water)
  - Group 3: Yellow-dominant (0.1 R / 0.7 Y / 0.1 B / 0.1 Water)
  - Group 4: Blue-dominant (0.1 R / 0.1 Y / 0.7 B / 0.1 Water)
- **Notes:** Most complete dataset. Has well plate images (144 center-crop JPEGs), composition map, trend plots (RGB/LAB/HSV), sensitivity analysis, stability analysis, and ANOVA. Labeled "BEST" — primary dataset for the paper.

---

### `20260313_110043_automated_6_2_1`
- **Date:** March 13, 2026
- **Method:** Automated
- **Ink ratio:** 6:2:1 (Red:Yellow:Blue)
- **Groups:**
  - Group 1: Red-dominant (0.6 R / 0.2 Y / 0.1 B / 0.1 Water)
  - Group 2: Yellow-dominant (0.2 R / 0.6 Y / 0.1 B / 0.1 Water)
  - Group 3: Blue-dominant (0.2 R / 0.1 Y / 0.6 B / 0.1 Water)
  - Group 4: Neutral (0.3 R / 0.3 Y / 0.3 B / 0.1 Water)
- **Notes:** Different ratio from BEST run. Has composition map and full analysis. No well images saved.

---

## Cross-Experiment Analysis

The `analysis/` subfolder contains aggregated results across all datasets:
- `measurement_vs_process_uncertainty_summary.csv` — process uncertainty is 5–19× larger than measurement uncertainty across all runs; priming matters (no-priming run has the worst ratio)
- `sensitivity_coefficients_with_response_strength.csv` — which color channels respond most strongly to each dye
- `uncertainty_hierarchy_all_channels.csv` — full per-channel breakdown
- Corresponding `.png` plots
