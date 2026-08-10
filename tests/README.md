# Tests

Hardware and integration tests. Run from the repo root. All tests import from `base_workflow.py` in this folder, which handles path setup automatically.

Set `VIRTUAL = True` in any test to run without hardware connected.

## Hardware Tests

| Script | What it tests | What to expect |
|---|---|---|
| `actuator_test.py` | Actuator extend and retract | Actuator moves ~0.5 cm, audible sound |
| `cnc_test.py` | CNC homing and movement | CNC homes then moves to test positions |
| `camera_test.py` | Camera capture and color extraction | Captures an image and prints RGB/LAB/HSV values |
| `cnc_camera_test.py` | CNC movement + camera capture together | Moves to well positions and captures images |
| `dispenser_test.py` | Full dispenser: CNC + actuator + camera | End-to-end liquid transfer with imaging |

## Workflow Tests

| Script | What it does |
|---|---|
| `testing_flow.py` | Basic CNC + actuator liquid transfer between two wells. Good first check after setup. |
| `blowout_to_reservoir_4.py` | Runs a syringe blowout/clearing procedure into reservoir 4. Use to clear the needle. |
| `test_optimizers.py` | Imports and initializes all three optimizer backends (BayBE, gradient, convex) and checks they work. No hardware needed. |

## Utility Scripts

| Script | What it does |
|---|---|
| `camera_capture_only.py` | Captures images from a configurable list of well plate slots without moving the CNC. |
| `camera_capture_slots.py` | Moves the CNC to each slot position and captures images across multiple wells. |

## Subdirectories

- `analysis/` — Post-processing scripts for uncertainty measurement workflow outputs. See `analysis/README.md`.
- `archive/` — Old/superseded test scripts kept for reference.
- `calibration/` — Scripts for volume calibration of the dispenser.
