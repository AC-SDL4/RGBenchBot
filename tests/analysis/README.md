# Analysis Scripts

Post-processing and analysis tools for uncertainty measurement workflow outputs.

## Main Analysis Scripts

### `uncertainty_plot_and_stats.py`
Primary per-experiment analysis script. Run this on a single uncertainty experiment folder.

**Outputs:** trend plots (RGB/LAB/HSV), normalized channel CSVs (`R'`, `G'`, `B'`, LAB, HSV), expected-value overlays, group stats, ANOVA table.

```bash
python tests/analysis/uncertainty_plot_and_stats.py output/uncertainty_measurement_workflow/BEST_20260224_123236_automated_darkest_most_yellow_7_1_1
```

### `stability_sensitivity_analysis.py`
Deeper per-experiment analysis: stability (normalized std per channel), sensitivity (R² of each channel vs dye volumes), standardized regression coefficients, and combined stability-vs-sensitivity plots.

**Outputs:** heatmaps, bar charts, scatter plots, `stability_metrics.csv`, `sensitivity_coefficients.csv` — all saved into the experiment's folder.

```bash
python tests/analysis/stability_sensitivity_analysis.py output/uncertainty_measurement_workflow/BEST_20260224_123236_automated_darkest_most_yellow_7_1_1
```

### `concentration_calibration.py`
Fits a linear mixing model from normalized RGB values to dye volume fractions. Predicts composition per well and produces calibration plots. Imports helpers from `uncertainty_plot_and_stats.py`.

```bash
python tests/analysis/concentration_calibration.py output/uncertainty_measurement_workflow/BEST_20260224_123236_automated_darkest_most_yellow_7_1_1
```

## Validation / Utility Scripts

### `validate_normalized.py`
Sanity-checks a `normalized_channels.csv` file: verifies value ranges and sum-to-one constraints for each channel group (RGB, LAB, HSV). Run after `uncertainty_plot_and_stats.py`.

```bash
python tests/analysis/validate_normalized.py output/uncertainty_measurement_workflow/BEST_20260224_123236_automated_darkest_most_yellow_7_1_1/normalized_channels.csv
```

### `camera_srgb_check.py`
One-time hardware check: verifies the camera delivers 8-bit 3-channel frames and estimates whether the output is sRGB gamma-encoded. Run this when setting up a new camera or capture pipeline.

```bash
python tests/analysis/camera_srgb_check.py --device 0 --backend dshow --width 1280 --height 720
```

Saves a report and sample image to `output/cnc_camera_test/<timestamp>/camera_srgb_check/`.

### `make_post_conditioning_validation.py`
Generates a post-conditioning volume validation figure from hardcoded January 2026 calibration measurements. One-off script; not intended for regular use.

---

## Notes
- Expected compositions for each experiment are defined in `uncertainty_plot_and_stats.get_expected_compositions()`.
- RGB normalization uses sRGB gamma decode to linear-light before computing mixing fractions.
- The cross-experiment summary plots in `output/uncertainty_measurement_workflow/analysis/` were generated externally and are not reproducible from scripts in this folder.
