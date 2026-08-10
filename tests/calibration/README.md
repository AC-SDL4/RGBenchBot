# Calibration Scripts

Tools for measuring and validating the dispenser's volume accuracy. Run from the repo root.
The dispenser uses time-based control (actuator extension time → volume dispensed), so calibration maps time → volume using gravimetric measurement (weighing dispensed liquid).

Recalibrate every ~1200 transfers (~3 full 24-well plates). Replace the syringe every ~2000 transfers.

## Workflow

### Step 1 — Run a calibration experiment (hardware required)

| Script | What it does |
|---|---|
| `volume_calibration.py` | Main calibration: dispenses a range of target volumes and records the dispensed mass on a balance. Saves a timestamped CSV to `output/calibration/time_volume_<timestamp>/`. |
| `focused_time_retest.py` | Re-runs specific time values to refine the curve in a narrow range. |
| `focused_time_retest_2.py` | Variant of the above. |
| `focused_time_restest_tip_conditioning.py` | Retest with tip conditioning cycles before each dispense — tests whether conditioning improves accuracy. |
| `volume_validation.py` | Validates a completed calibration by dispensing target volumes and checking accuracy. |

### Step 2 — Process the raw data

| Script | What it does |
|---|---|
| `compute_net_mass.py` | Calculates net mass per dispense from a raw calibration CSV (subtracts tare, handles plate resets). |
| `parse_mass_log.py` | Parses the balance mass log file into a structured CSV. |
| `combine_time_net_csvs.py` | Merges multiple calibration run CSVs into one for cross-run analysis. |

### Step 3 — Analyze and plot

| Script | What it does |
|---|---|
| `time_net_mass_analysis.py` | Builds the time→volume curve and fits a linear model. Uses latest CSV under `output/calibration/` by default. |
| `volume_time_analysis.py` | Alternative analysis of the time→volume relationship. |
| `volume_validation_analysis.py` | Analyzes validation data — compares target vs dispensed volumes. |
| `plot_multi_runs.py` | Overlays multiple calibration runs on one plot for drift comparison. |
| `plot_volume_csv.py` | Plots a single calibration CSV. |

## Shared

| File | What it contains |
|---|---|
| `constants.py` | Shared hardware constants: max actuator time, calibration replicates, speed settings. |
