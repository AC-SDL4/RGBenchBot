"""
Colorspace comparison for March 2026 color-matching runs — LAB / RGB / HSV only.

All three use BayBE optimizer, same target recipe:
  Target recipe: R=0.40 mL, Y=0.55 mL, B=0.05 mL
"""

import pandas as pd
import numpy as np
import pathlib
import matplotlib.pyplot as plt
import sys
sys.stdout.reconfigure(encoding="utf-8")

ROOT = pathlib.Path(r"C:\Users\owenm\OneDrive\Desktop\Master Budget Dispenser\actuator-dispenser")
BASE = ROOT / "output" / "color_matching_workflow" / "Color_Matching_BO_March2026"
OUT  = ROOT / "output" / "color_matching_workflow" / "analysis"

TARGET_R, TARGET_Y, TARGET_B = 0.40, 0.55, 0.05

STEP = 0.05
D1   = np.sqrt(2) * STEP
D2   = np.sqrt(2) * 2 * STEP
TIE_TOL = 1e-4

runs = [
    ("20260320_081432_LAB",                  "LAB"),
    ("20260320_102831_RGB",                  "RGB"),
    ("20260320_123918_HSV_No_AllWells_Photo", "HSV"),
]

COLORS = {"LAB": "#1f77b4", "RGB": "#ff7f0e", "HSV": "#2ca02c"}


def steps_from_d(d):
    return d / (np.sqrt(2) * STEP)


# ── collect per-run stats ──────────────────────────────────────────────────────
results = []
run_dfs = {}

for folder, label in runs:
    df   = pd.read_csv(BASE / folder / "color_matching_results.csv")
    data = df[df["well"] != "Target"].copy()
    data["well_num"] = pd.to_numeric(data["well"], errors="coerce")
    data = data.dropna(subset=["well_num"]).sort_values("well_num").reset_index(drop=True)

    data["d_input"] = np.sqrt(
        (data["R_volume_ml"] - TARGET_R)**2 +
        (data["Y_volume_ml"] - TARGET_Y)**2 +
        (data["B_volume_ml"] - TARGET_B)**2
    )

    n_total = len(data)
    d_min   = data["d_input"].min()
    n_hits1 = (data["d_input"] <= D1 + 1e-9).sum()
    n_hits2 = (data["d_input"] <= D2 + 1e-9).sum()

    best_obj_idx  = data["output"].idxmin()
    best_obj_row  = data.loc[best_obj_idx]
    best_obj_d    = best_obj_row["d_input"]

    global_best_obj  = data["output"].min()
    data["run_min"]  = data["output"].expanding().min()
    first_found_iter = int(data.loc[(data["run_min"] <= global_best_obj + 1e-9).idxmax(), "well_num"])

    hits1_mask       = data["d_input"] <= D1 + 1e-9
    first_1step_iter = int(data.loc[hits1_mask, "well_num"].min()) if hits1_mask.any() else None

    best_d_row = data.loc[data["d_input"].idxmin()]

    tied_mask   = data["d_input"] <= d_min + TIE_TOL
    n_tied      = int(tied_mask.sum())
    obj_correct = best_obj_d <= d_min + TIE_TOL
    steps_obj   = steps_from_d(best_obj_d)
    steps_best  = steps_from_d(d_min)
    steps_gap   = steps_obj - steps_best

    if obj_correct:
        alignment_str = f"YES — picked 1 of {n_tied} tied well(s) at {steps_best:.1f} steps"
    else:
        alignment_str = (
            f"NO  — objective picked {steps_obj:.1f} steps; "
            f"true best was {steps_best:.1f} steps ({steps_gap:+.1f} gap); "
            f"{n_tied} well(s) tied at best"
        )

    results.append({
        "label":            label,
        "n_total":          n_total,
        "d_min_mL":         round(d_min, 4),
        "steps_off":        round(steps_best, 2),
        "n_hits_1step":     int(n_hits1),
        "pct_hits_1step":   round(100 * n_hits1 / n_total, 1),
        "n_hits_2step":     int(n_hits2),
        "pct_hits_2step":   round(100 * n_hits2 / n_total, 1),
        "first_found_iter": first_found_iter,
        "pct_used_to_find": round(100 * first_found_iter / n_total, 1),
        "first_1step_iter": first_1step_iter,
        "pct_used_1step":   round(100 * first_1step_iter / n_total, 1) if first_1step_iter is not None else None,
        "obj_correct":      obj_correct,
        "n_tied_at_best":   n_tied,
        "steps_obj":        round(steps_obj, 2),
        "steps_best":       round(steps_best, 2),
        "steps_gap":        round(steps_gap, 2),
        "alignment_str":    alignment_str,
        "best_obj_R":       best_obj_row["R_volume_ml"],
        "best_obj_Y":       best_obj_row["Y_volume_ml"],
        "best_obj_B":       best_obj_row["B_volume_ml"],
        "best_obj_d":       round(best_obj_d, 4),
        "best_d_R":         best_d_row["R_volume_ml"],
        "best_d_Y":         best_d_row["Y_volume_ml"],
        "best_d_B":         best_d_row["B_volume_ml"],
    })
    run_dfs[label] = data

summary = pd.DataFrame(results)

# ── print summary ──────────────────────────────────────────────────────────────
print("=" * 72)
print(f"TARGET: R={TARGET_R}  Y={TARGET_Y}  B={TARGET_B}")
print(f"Grid step: {STEP} mL  |  D1 ~= {D1:.4f} mL  |  D2 ~= {D2:.4f} mL")
print("=" * 72)

for r in results:
    print(f"\n{'─'*60}")
    print(f"  {r['label']}  ({r['n_total']} wells)")
    print(f"  1. Accuracy:    d_min = {r['d_min_mL']:.4f} mL  ~= {r['steps_off']:.2f} grid steps")
    print(f"                  best-by-composition: R={r['best_d_R']:.2f}  Y={r['best_d_Y']:.2f}  B={r['best_d_B']:.2f}")
    print(f"  2. Hit density: ≤1 step: {r['n_hits_1step']:2d}/{r['n_total']}   ≤2 steps: {r['n_hits_2step']:2d}/{r['n_total']}")
    print(f"  3. Alignment:   {r['alignment_str']}")

print(f"\n{'='*72}")
print(summary[["label","d_min_mL","steps_off","n_hits_1step","n_hits_2step","obj_correct","steps_gap"]].to_string(index=False))

# ── save CSVs ──────────────────────────────────────────────────────────────────
csv_summary = OUT / "mar26_colorspace_comparison.csv"
summary.to_csv(csv_summary, index=False)
print(f"\nSummary CSV saved → {csv_summary}")

conv_df = pd.DataFrame({"well": run_dfs[list(run_dfs)[0]]["well_num"].values})
for label, data in run_dfs.items():
    conv_df[f"d_input_{label}"]     = data["d_input"].values
    conv_df[f"best_so_far_{label}"] = data["d_input"].expanding().min().values
csv_conv = OUT / "mar26_colorspace_comparison_convergence.csv"
conv_df.to_csv(csv_conv, index=False)
print(f"Convergence CSV saved → {csv_conv}")

# ── figure ─────────────────────────────────────────────────────────────────────
labels     = [r["label"] for r in results]
x          = np.arange(len(labels))
bar_colors = [COLORS[l] for l in labels]
n_total    = results[0]["n_total"]

fig = plt.figure(figsize=(13, 5), constrained_layout=True)
gs  = fig.add_gridspec(2, 2, width_ratios=[1, 1.6], hspace=0.12)
ax_acc  = fig.add_subplot(gs[0, 0])
ax_hit  = fig.add_subplot(gs[1, 0])
ax_conv = fig.add_subplot(gs[:, 1])

# panel A top: d_min
bars = ax_acc.bar(x, [r["d_min_mL"] for r in results],
                  color=bar_colors, edgecolor="k", linewidth=0.8, zorder=3)
ax_acc.axhline(D1, color="dimgrey", ls="--", lw=1.2, zorder=2, label=f"1 step ({D1:.3f} mL)")
ax_acc.axhline(D2, color="dimgrey", ls=":",  lw=1.2, zorder=2, label=f"2 steps ({D2:.3f} mL)")
for bar, r in zip(bars, results):
    cx, h = bar.get_x() + bar.get_width() / 2, bar.get_height()
    steps = int(round(r["steps_off"]))
    label_str = "exact" if steps == 0 else f"{steps} step{'s' if steps != 1 else ''}"
    ax_acc.text(cx, h + 0.005, label_str, ha="center", va="bottom", fontsize=9)
ax_acc.set_xticks(x); ax_acc.set_xticklabels([])
ax_acc.set_ylabel("d_min (mL)")
ax_acc.set_ylim(0, max(r["d_min_mL"] for r in results) * 1.5)
ax_acc.set_title("A. Accuracy & hit density", fontsize=10, loc="left")
ax_acc.legend(fontsize=7.5, loc="upper right")
ax_acc.grid(axis="y", alpha=0.3, zorder=0)

# panel A bottom: hit count
bars2 = ax_hit.bar(x, [r["n_hits_1step"] for r in results],
                   color=bar_colors, edgecolor="k", linewidth=0.8, zorder=3)
for bar, r in zip(bars2, results):
    cx, h = bar.get_x() + bar.get_width() / 2, bar.get_height()
    ax_hit.text(cx, h + 0.1, f"{r['n_hits_1step']}/{n_total}",
                ha="center", va="bottom", fontsize=9)
ax_hit.set_xticks(x); ax_hit.set_xticklabels(labels, fontsize=10)
ax_hit.set_ylabel(f"Wells within 1 step (out of {n_total})")
ax_hit.set_ylim(0, max(r["n_hits_1step"] for r in results) * 1.5 + 1)
ax_hit.grid(axis="y", alpha=0.3, zorder=0)

# panel B: convergence
for label, data in run_dfs.items():
    ax_conv.plot(data["well_num"], data["d_input"].expanding().min(),
                 color=COLORS[label], lw=2.2, label=label)
ax_conv.axhline(D1, color="dimgrey", ls="--", lw=1.2, label=f"1-step ({D1:.3f} mL)")
ax_conv.axhline(D2, color="dimgrey", ls=":",  lw=1.2, label=f"2-step ({D2:.3f} mL)")
ax_conv.set_xlabel("Well # (iteration order)")
ax_conv.set_ylabel("Best-so-far composition distance (mL)")
ax_conv.set_title("B. Convergence", fontsize=10, loc="left")
ax_conv.legend(fontsize=9)
ax_conv.grid(alpha=0.3)
ax_conv.set_xlim(1, n_total)

fig.suptitle(
    f"Colorspace comparison — March 2026 (BayBE)  |  Target: R={TARGET_R} Y={TARGET_Y} B={TARGET_B} mL",
    fontsize=11
)

fig_out = OUT / "mar26_colorspace_comparison.png"
fig.savefig(fig_out, dpi=150, bbox_inches="tight")
print(f"Figure saved → {fig_out}")

plt.show()
