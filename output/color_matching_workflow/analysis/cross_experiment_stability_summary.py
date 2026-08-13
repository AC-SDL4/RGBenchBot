"""
Cross-experiment stability summary.

Loads stability_sensitivity_combined.csv from each uncertainty experiment's
analysis/ subfolder, merges into a single CSV, and produces:
  - stability_summary_all_experiments.csv  (long-form, one row per channel×exp)
  - stability_heatmap.png                  (channels × experiments, color = norm_std)
  - stability_bar_chart.png                (mean ± std per channel across experiments)

Output is written to output/uncertainty_measurement_workflow/noise_analysis/.
"""

import sys
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
UMW = ROOT / "output" / "uncertainty_measurement_workflow"
OUT = UMW / "noise_analysis"
OUT.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------
# Experiment registry: folder name → short display label
# ------------------------------------------------------------------
EXPERIMENTS = [
    ("20260130_143830_automated_5_2_2",
     "Jan 30\n(5:2:2)"),
    ("20260210_150847_automated_darkest_7_1_1",
     "Feb 10\n(7:1:1 dark)"),
    ("no_priming_20260213_073533_automated_darkest_more_yellow_7_1_1_group1_2_4",
     "Feb 13\n(no prime)"),
    ("20260218_141247_manual_pipett_by_hand",
     "Feb 18\n(manual)"),
    ("BEST_20260224_123236_automated_darkest_most_yellow_7_1_1",
     "Feb 24\n(BEST)"),
    ("20260313_110043_automated_6_2_1",
     "Mar 13\n(6:2:1)"),
]

# ------------------------------------------------------------------
# Load data
# ------------------------------------------------------------------
frames = []
for folder, label in EXPERIMENTS:
    csv_path = UMW / folder / "analysis" / "stability_sensitivity_combined.csv"
    if not csv_path.exists():
        print(f"WARNING: missing {csv_path}")
        continue
    df = pd.read_csv(csv_path)
    df["experiment"] = label
    df["folder"] = folder
    frames.append(df[["experiment", "folder", "channel", "channel_type", "norm_std"]])

if not frames:
    print("No experiment data found.")
    sys.exit(1)

combined = pd.concat(frames, ignore_index=True)

# ------------------------------------------------------------------
# Save long-form CSV
# ------------------------------------------------------------------
csv_out = OUT / "stability_summary_all_experiments.csv"
combined.to_csv(csv_out, index=False)
print(f"Saved: {csv_out}")

# ------------------------------------------------------------------
# Pivot to wide form for plotting: channels (rows) × experiments (cols)
# ------------------------------------------------------------------
pivot = combined.pivot_table(index="channel", columns="experiment", values="norm_std")

# Order columns chronologically
col_order = [label for _, label in EXPERIMENTS if label in pivot.columns]
pivot = pivot[col_order]

# Sort channels: raw channels first (alphabetically), then normalized
raw_channels = sorted(combined[combined.channel_type == "raw"]["channel"].unique())
norm_channels = sorted(combined[combined.channel_type == "normalized"]["channel"].unique())
channel_order = raw_channels + norm_channels
pivot = pivot.reindex([c for c in channel_order if c in pivot.index])

# Within each group, sort by mean stability (best = lowest norm_std first)
raw_pivot = pivot.loc[[c for c in raw_channels if c in pivot.index]]
norm_pivot = pivot.loc[[c for c in norm_channels if c in pivot.index]]
raw_pivot = raw_pivot.loc[raw_pivot.mean(axis=1).sort_values().index]
norm_pivot = norm_pivot.loc[norm_pivot.mean(axis=1).sort_values().index]
pivot = pd.concat([raw_pivot, norm_pivot])

# ------------------------------------------------------------------
# Heatmap
# ------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(10, 7))

data = pivot.values.astype(float)
im = ax.imshow(data, aspect="auto", cmap="YlOrRd", vmin=0)

ax.set_xticks(range(len(pivot.columns)))
ax.set_xticklabels(pivot.columns, fontsize=9)
ax.set_yticks(range(len(pivot.index)))
ax.set_yticklabels(pivot.index, fontsize=9)

# Annotate cells
for i in range(data.shape[0]):
    for j in range(data.shape[1]):
        val = data[i, j]
        if not np.isnan(val):
            color = "white" if val > np.nanmax(data) * 0.6 else "black"
            ax.text(j, i, f"{val:.4f}", ha="center", va="center",
                    fontsize=7, color=color)

# Divider between raw and normalized sections
div = len(raw_pivot) - 0.5
ax.axhline(div, color="black", linewidth=1.5, linestyle="--")
ax.text(len(pivot.columns) - 0.05, div - 0.6, "raw", ha="right",
        va="center", fontsize=8, color="gray")
ax.text(len(pivot.columns) - 0.05, div + 0.6, "normalized", ha="right",
        va="center", fontsize=8, color="gray")

plt.colorbar(im, ax=ax, label="norm_std (lower = more stable)", shrink=0.8)
ax.set_title("Channel Stability Across All Experiments\n(norm_std — lower is better)",
             fontsize=11, pad=12)
plt.tight_layout()
heatmap_out = OUT / "stability_heatmap.png"
fig.savefig(heatmap_out, dpi=150)
plt.close(fig)
print(f"Saved: {heatmap_out}")

# ------------------------------------------------------------------
# Bar chart: mean ± std across experiments, per channel
# ------------------------------------------------------------------
mean_std = combined.groupby(["channel", "channel_type"])["norm_std"].agg(
    mean="mean", std="std"
).reset_index()

# Apply same ordering
mean_std["channel_type_order"] = mean_std["channel_type"].map({"raw": 0, "normalized": 1})
mean_std = mean_std.sort_values(["channel_type_order", "mean"])

raw_ms = mean_std[mean_std.channel_type == "raw"]
norm_ms = mean_std[mean_std.channel_type == "normalized"]

fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=False)

for ax, subset, title, color in [
    (axes[0], raw_ms, "Raw Channels", "#3b82f6"),
    (axes[1], norm_ms, "Normalized Channels", "#f97316"),
]:
    ax.bar(range(len(subset)), subset["mean"], yerr=subset["std"].fillna(0),
           color=color, alpha=0.8, capsize=4, ecolor="black", linewidth=0.5,
           edgecolor="black")
    ax.set_xticks(range(len(subset)))
    ax.set_xticklabels(subset["channel"], rotation=45, ha="right", fontsize=9)
    ax.set_ylabel("norm_std (lower = more stable)")
    ax.set_title(title)
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    # Annotate values
    for i, (_, row) in enumerate(subset.iterrows()):
        ax.text(i, row["mean"] + (row["std"] if not np.isnan(row["std"]) else 0) + 0.0005,
                f'{row["mean"]:.4f}', ha="center", va="bottom", fontsize=7, rotation=0)

fig.suptitle("Mean Channel Stability Across All 6 Experiments\n(error bars = std across experiments)",
             fontsize=11)
plt.tight_layout()
bar_out = OUT / "stability_bar_chart.png"
fig.savefig(bar_out, dpi=150)
plt.close(fig)
print(f"Saved: {bar_out}")

print("\nDone.")
