# Workflows

Run these from the repo root. All workflows import from `base_workflow.py` for hardware initialization and logging.

## Experiment Workflows

| Script | Description |
|---|---|
| `color_matching_workflow.py` | Main workflow: iterative Bayesian optimization to match a target color by mixing Red, Yellow, and Blue solutions. Supports `baybe`, `gradient`, and `convex` optimizer backends (set `OPTIMIZER_TYPE` at top of file). |
| `color_maximizing_workflow.py` | Maximize color intensity across multiple components using Bayesian optimization (BayBE). |
| `uncertainty_measurement_workflow.py` | Dispense known mixtures into a 24-well plate (4 groups × 6 replicates) and image each well repeatedly to measure dispensing repeatability. Set `MANUAL_MODE = True` to image manually-prepared wells instead. |
| `titration_demo.py` | Acid-base titration (HCl + NaOH): iteratively adds NaOH and captures color at each step. |
| `titration_demo_gui.py` | GUI wrapper for `titration_demo.py`. |
| `titration.py` | Minimal titration script (no GUI, no priming). Simpler alternative to `titration_demo.py`. |
| `gradient_workflow.py` | Creates a 2D color gradient across a 24-well plate by varying Yellow and Blue volumes systematically. |
| `multi_well_percentage_dispenser.py` | Dispenses user-defined percentage compositions of multiple colorants into separate wells. |
| `multi_well_percentage_dispenser_gui.py` | GUI wrapper for `multi_well_percentage_dispenser.py`. |

## Optimizer Backends (used by `color_matching_workflow.py`)

| Script | Description |
|---|---|
| `color_matching_optimizer.py` | BayBE Bayesian optimizer |
| `color_matching_gradient_optimizer.py` | Gradient descent optimizer |
| `color_matching_convex_optimizer.py` | Convex optimization solver |
| `shared_color_initialization.py` | Shared color target setup used across optimizer backends |

## Utilities

| Script | Description |
|---|---|
| `capture_slot_colors.py` | Images a set of well plate slots and records RGB/LAB/HSV values. Useful for inspecting manually-prepared wells without running a full experiment. |
| `example_workflow.py` | Minimal template showing basic dispenser usage. Good starting point for new workflows. |
| `base_workflow.py` | Shared imports and logging setup. Import this instead of importing hardware classes directly. |
