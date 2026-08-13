"""
Compare two stability metrics across all 6 experiments:

  norm_std_theoretical  = within-group noise / theoretical channel max range
  norm_std_practical    = within-group noise / actual observed range (max-min across all wells)

Outputs to output/uncertainty_measurement_workflow/noise_analysis/:
  stability_metric_comparison.csv   -- both metrics per channel per experiment
  stability_metric_comparison.png   -- side-by-side heatmaps + rank change table
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

ROOT = Path(__file__).resolve().parents[2]
UMW = ROOT / "output" / "uncertainty_measurement_workflow"
OUT = UMW / "noise_analysis"
OUT.mkdir(parents=True, exist_ok=True)

EXPERIMENTS = [
    ("20260130_143830_automated_5_2_2",                                              "Jan 30\n(5:2:2)"),
    ("20260210_150847_automated_darkest_7_1_1",                                      "Feb 10\n(7:1:1 dark)"),
    ("no_priming_20260213_073533_automated_darkest_more_yellow_7_1_1_group1_2_4",    "Feb 13\n(no prime)"),
    ("20260218_141247_manual_pipett_by_hand",                                        "Feb 18\n(manual)"),
    ("BEST_20260224_123236_automated_darkest_most_yellow_7_1_1",                     "Feb 24\n(BEST)"),
    ("20260313_110043_automated_6_2_1",                                              "Mar 13\n(6:2:1)"),
]

RAW_CHANNELS  = ['RGB_R', 'RGB_G', 'RGB_B', 'LAB_L', 'LAB_A', 'LAB_B', 'HSV_H', 'HSV_S', 'HSV_V']
NORM_CHANNELS = ["R'", "G'", "B'", "L'", "C'", "h'", "H'", "S'", "V'"]

THEORETICAL_RANGES = {
    'RGB_R': 255, 'RGB_G': 255, 'RGB_B': 255,
    'LAB_L': 100, 'LAB_A': 255, 'LAB_B': 255,
    'HSV_H': 360, 'HSV_S': 100, 'HSV_V': 100,
    **{c: 1.0 for c in NORM_CHANNELS},
}

# -----------------------------------------------------------------------
# Compute both metrics from raw data
# -----------------------------------------------------------------------
records = []

for folder, label in EXPERIMENTS:
    exp_dir = UMW / folder
    raw_csv  = exp_dir / "uncertainty_measurements_raw.csv"
    norm_csv = exp_dir / "normalized_channels.csv"

    if not raw_csv.exists():
        print(f"WARNING: no raw csv in {folder}")
        continue

    raw_df  = pd.read_csv(raw_csv)
    norm_df = pd.read_csv(norm_csv) if norm_csv.exists() else None

    # --- Raw channels ---
    for ch in RAW_CHANNELS:
        if ch not in raw_df.columns:
            continue
        # Within-well replicate noise: std per well, then average across all wells
        within_noise = raw_df.groupby("well_index")[ch].std(ddof=1).mean()
        actual_range = raw_df[ch].max() - raw_df[ch].min()

        records.append({
            "experiment": label,
            "channel": ch,
            "channel_type": "raw",
            "within_noise": within_noise,
            "theoretical_range": THEORETICAL_RANGES[ch],
            "actual_range": actual_range,
            "norm_std_theoretical": within_noise / THEORETICAL_RANGES[ch],
            "norm_std_practical":   within_noise / actual_range if actual_range > 0 else np.nan,
        })

    # --- Normalized channels ---
    if norm_df is not None:
        # normalized_channels.csv: one row per well per channel (long form)
        # pivot to wide so each well is one row
        norm_wide = norm_df.pivot_table(
            index=["group_id", "well_index"], columns="channel", values="value"
        ).reset_index()

        for ch in NORM_CHANNELS:
            if ch not in norm_wide.columns:
                continue
            # Within-group noise: std of wells within each group, averaged across groups
            within_noise = norm_wide.groupby("group_id")[ch].std(ddof=1).mean()
            actual_range = norm_wide[ch].max() - norm_wide[ch].min()

            records.append({
                "experiment": label,
                "channel": ch,
                "channel_type": "normalized",
                "within_noise": within_noise,
                "theoretical_range": THEORETICAL_RANGES[ch],
                "actual_range": actual_range,
                "norm_std_theoretical": within_noise / THEORETICAL_RANGES[ch],
                "norm_std_practical":   within_noise / actual_range if actual_range > 0 else np.nan,
            })

df = pd.DataFrame(records)

# Save CSV
csv_out = OUT / "stability_metric_comparison.csv"
df.to_csv(csv_out, index=False)
print(f"Saved: {csv_out}")

# -----------------------------------------------------------------------
# Build pivot tables for heatmaps
# -----------------------------------------------------------------------
col_order = [label for _, label in EXPERIMENTS]

raw_channels  = [c for c in RAW_CHANNELS  if c in df["channel"].unique()]
norm_channels = [c for c in NORM_CHANNELS if c in df["channel"].unique()]
channel_order = raw_channels + norm_channels

def make_pivot(metric):
    p = df.pivot_table(index="channel", columns="experiment", values=metric)
    p = p[[c for c in col_order if c in p.columns]]
    # Sort: raw first by mean, then normalized by mean
    rp = p.loc[[c for c in raw_channels  if c in p.index]]
    np_ = p.loc[[c for c in norm_channels if c in p.index]]
    rp  = rp.loc[rp.mean(axis=1).sort_values().index]
    np_ = np_.loc[np_.mean(axis=1).sort_values().index]
    return pd.concat([rp, np_])

piv_theoretical = make_pivot("norm_std_theoretical")
piv_practical   = make_pivot("norm_std_practical")

# shared colour scale max (cap at 99th pctile to avoid outliers dominating)
vmax_t = np.nanpercentile(piv_theoretical.values.astype(float), 99)
vmax_p = np.nanpercentile(piv_practical.values.astype(float), 99)

# -----------------------------------------------------------------------
# Rank comparison (mean across experiments)
# -----------------------------------------------------------------------
mean_t = df.groupby(["channel","channel_type"])["norm_std_theoretical"].mean().rename("mean_theoretical")
mean_p = df.groupby(["channel","channel_type"])["norm_std_practical"].mean().rename("mean_practical")
rank_df = pd.concat([mean_t, mean_p], axis=1).reset_index()
rank_df["rank_theoretical"] = rank_df["mean_theoretical"].rank().astype(int)
rank_df["rank_practical"]   = rank_df["mean_practical"].rank().astype(int)
rank_df["rank_change"]      = rank_df["rank_practical"] - rank_df["rank_theoretical"]

# Sort by theoretical rank for display
rank_df = rank_df.sort_values("rank_theoretical").reset_index(drop=True)

# -----------------------------------------------------------------------
# Figure
# -----------------------------------------------------------------------
fig = plt.figure(figsize=(18, 11))
gs  = gridspec.GridSpec(1, 3, width_ratios=[5, 5, 4], figure=fig, wspace=0.45)

ax_t  = fig.add_subplot(gs[0])
ax_p  = fig.add_subplot(gs[1])
ax_r  = fig.add_subplot(gs[2])

div = len([c for c in raw_channels if c in piv_theoretical.index]) - 0.5

def draw_heatmap(ax, pivot, vmax, title):
    data = pivot.values.astype(float)
    im = ax.imshow(data, aspect="auto", cmap="YlOrRd", vmin=0, vmax=vmax)
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns, fontsize=8)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index, fontsize=9)
    ax.axhline(div, color="black", linewidth=1.5, linestyle="--")
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            v = data[i, j]
            if not np.isnan(v):
                color = "white" if v > vmax * 0.6 else "black"
                ax.text(j, i, f"{v:.4f}", ha="center", va="center", fontsize=6.5, color=color)
    ax.set_title(title, fontsize=10, pad=8)
    plt.colorbar(im, ax=ax, shrink=0.7, label="stability (lower = better)")

draw_heatmap(ax_t, piv_theoretical, vmax_t, "Theoretical norm_std\n(÷ max possible range)")
draw_heatmap(ax_p, piv_practical,   vmax_p, "Practical norm_std\n(÷ actual observed range)")

# --- Rank table ---
ax_r.axis("off")
col_labels = ["Channel", "Type", "Rank\ntheor.", "Rank\npract.", "Δ rank"]
table_data = []
for _, row in rank_df.iterrows():
    delta = row["rank_change"]
    delta_str = f"+{int(delta)}" if delta > 0 else str(int(delta))
    table_data.append([row["channel"], row["channel_type"][:4],
                       str(row["rank_theoretical"]), str(row["rank_practical"]), delta_str])

tbl = ax_r.table(
    cellText=table_data,
    colLabels=col_labels,
    loc="center",
    cellLoc="center",
)
tbl.auto_set_font_size(False)
tbl.set_fontsize(8.5)
tbl.scale(1, 1.35)

# Colour rows by rank change magnitude
for i, (_, row) in enumerate(rank_df.iterrows()):
    delta = abs(row["rank_change"])
    if delta >= 4:
        colour = "#fca5a5"   # red — significant change
    elif delta >= 2:
        colour = "#fde68a"   # yellow — moderate
    else:
        colour = "#d1fae5"   # green — stable rank
    for j in range(len(col_labels)):
        tbl[(i + 1, j)].set_facecolor(colour)

ax_r.set_title("Rank change\n(green=stable, red=shifted ≥4)", fontsize=9, pad=8)

fig.suptitle(
    "Stability Metric Comparison: Theoretical vs Practical Normalisation\n"
    "Both measure: within-group noise / range   —   does the normaliser change channel rankings?",
    fontsize=10, y=1.01
)
plt.tight_layout()

out_fig = OUT / "stability_metric_comparison.png"
fig.savefig(out_fig, dpi=150, bbox_inches="tight")
plt.close(fig)
print(f"Saved: {out_fig}")

# -----------------------------------------------------------------------
# Print rank changes to console
# -----------------------------------------------------------------------
print("\n=== RANK COMPARISON (mean across 6 experiments) ===")
print(f"{'Channel':<10} {'Type':<11} {'Rank(theor)':<13} {'Rank(pract)':<13} {'Δ':<5}")
print("-" * 55)
for _, row in rank_df.iterrows():
    d = int(row["rank_change"])
    flag = "  <<< CHANGED" if abs(d) >= 4 else ""
    print(f"{row['channel']:<10} {row['channel_type']:<11} {int(row['rank_theoretical']):<13} "
          f"{int(row['rank_practical']):<13} {d:+d}{flag}")

print("\nDone.")
