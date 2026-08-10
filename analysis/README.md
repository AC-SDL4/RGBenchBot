# Analysis Scripts

Post-run analysis tools for color matching and uncertainty experiments. Run from the repo root.

## Color Matching Analysis

### `color_matching_analysis.py` — CLI
Analyzes a `color_matching_results.csv` from a completed color matching run. Reports how close the optimizer got to the target color (output score) and how close the dispensed compositions were to the target recipe (R/Y/B volumes).

```bash
python analysis/color_matching_analysis.py output/color_matching_workflow/<run_folder>
```

### `color_matching_analysis_gui.py` — GUI
Tkinter GUI version of the above. Supports single-run analysis, multi-folder comparison, drag-and-drop, and embedded plots. Saves preferences between sessions.

```bash
python analysis/color_matching_analysis_gui.py
```

## Uncertainty Analysis

### `yellow_sensitivity_comparison.py`
Compares two uncertainty experiment runs with different yellow ink concentrations ("more yellow" vs "most yellow") to evaluate which color channels best distinguish yellow concentration changes, using R² as the metric.

```bash
python analysis/yellow_sensitivity_comparison.py
```
