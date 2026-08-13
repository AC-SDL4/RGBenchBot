"""
Build Table X: Noise ratio table for the paper.

Reads raw per-image measurements for the two experiments used in the table,
computes sigma_meas and sigma_proc per group x channel, then derives the 4
ratios reported in Table X (median over 3 channels x 4 groups per colorspace).

Sources:
  BEST_20260224  -> "Automated 7:1:1 primary"
  20260218       -> "Manual 7:1:1"

Outputs:
  output/uncertainty_measurement_workflow/noise_analysis/noise_per_group_channel.csv
      one row per (dataset, group_id, channel): sigma_meas, sigma_proc, ratio
  output/uncertainty_measurement_workflow/noise_analysis/noise_table.csv
      the 4x3 table (rows = ratio type, cols = RGB/LAB/HSV)
"""

import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(__file__).parent
UMW  = ROOT / "output" / "uncertainty_measurement_workflow"
OUT  = UMW / "noise_analysis"
OUT.mkdir(parents=True, exist_ok=True)

CHANNELS = ['RGB_R', 'RGB_G', 'RGB_B', 'LAB_L', 'LAB_A', 'LAB_B', 'HSV_H', 'HSV_S', 'HSV_V']
CS_MAP   = {'RGB': ['RGB_R', 'RGB_G', 'RGB_B'],
            'LAB': ['LAB_L', 'LAB_A', 'LAB_B'],
            'HSV': ['HSV_H', 'HSV_S', 'HSV_V']}

EXPERIMENTS = [
    ("BEST_20260224_123236_automated_darkest_most_yellow_7_1_1", "Automated 7:1:1 primary"),
    ("20260218_141247_manual_pipett_by_hand",                    "Manual 7:1:1"),
]


def compute_per_group_channel(raw: pd.DataFrame, dataset: str) -> pd.DataFrame:
    rows = []
    for gid in sorted(raw['group_id'].unique()):
        g = raw[raw['group_id'] == gid]
        for ch in CHANNELS:
            if ch not in g.columns:
                continue
            sigma_meas = g.groupby('well_index')[ch].std(ddof=1).mean()
            sigma_proc = g.groupby('well_index')[ch].mean().std(ddof=1)
            rows.append({
                'dataset':      dataset,
                'group_id':     int(gid),
                'channel':      ch,
                'sigma_meas':   sigma_meas,
                'sigma_proc':   sigma_proc,
                'ratio':        sigma_proc / sigma_meas if sigma_meas > 0 else np.nan,
            })
    return pd.DataFrame(rows)


# --- Load and compute ---
parts = []
for folder, label in EXPERIMENTS:
    raw_path = UMW / folder / "uncertainty_measurements_raw.csv"
    raw = pd.read_csv(raw_path)
    parts.append(compute_per_group_channel(raw, label))

per_group = pd.concat(parts, ignore_index=True)
per_group.to_csv(OUT / "noise_per_group_channel.csv", index=False, float_format='%.6f')
print(f"Saved: {OUT / 'noise_per_group_channel.csv'}  ({len(per_group)} rows)")

# --- Build 4x3 table ---
auto = per_group[per_group['dataset'] == 'Automated 7:1:1 primary']
man  = per_group[per_group['dataset'] == 'Manual 7:1:1']
merged = auto.merge(man, on=['channel', 'group_id'], suffixes=('_auto', '_man'))

merged['r1'] = merged['sigma_proc_auto'] / merged['sigma_meas_auto']   # row 1
merged['r2'] = merged['sigma_proc_man']  / merged['sigma_meas_man']    # row 2
merged['r3'] = merged['sigma_proc_auto'] / merged['sigma_proc_man']    # row 3
merged['r4'] = merged['sigma_meas_auto'] / merged['sigma_meas_man']    # row 4

table_rows = []
row_labels = [
    ('sigma_well_auto / sigma_meas_auto',   'r1'),
    ('sigma_well_manual / sigma_meas_manual', 'r2'),
    ('sigma_well_auto / sigma_well_manual',  'r3'),
    ('sigma_meas_auto / sigma_meas_manual',  'r4'),
]
for label, col in row_labels:
    row = {'Noise Ratio': label}
    for cs, chans in CS_MAP.items():
        vals = merged[merged['channel'].isin(chans)][col]
        row[cs] = round(float(np.median(vals)), 2)
    table_rows.append(row)

table = pd.DataFrame(table_rows).set_index('Noise Ratio')
table.to_csv(OUT / "noise_table.csv", float_format='%.2f')
print(f"Saved: {OUT / 'noise_table.csv'}")
print()
print(table.to_string())
print()
print(f"n per cell: {len(merged[merged['channel'].isin(CS_MAP['RGB'])])}  (3 channels x 4 groups)")
