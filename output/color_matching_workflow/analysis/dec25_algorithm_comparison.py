"""
Algorithm comparison for Dec 2025 color-matching runs.

Compares 4 algorithms (all using LAB colorspace, same target recipe):
  Random, BayBE, Gradient, Convex

Target recipe: R=0.30 mL, Y=0.20 mL, B=0.50 mL  (300 / 200 / 500 µL)

Five metrics per run:
  1. Speed          — % of 23-well budget used before the best-by-objective well was first found
  2. Accuracy       — d_min_mL: closest any well got to the target recipe (composition space)
  3. Hit density 1  — % of wells within 1 grid step of target (~0.07 mL)
  4. Hit density 2  — % of wells within 2 grid steps of target (~0.14 mL)
  5. Alignment      — does the algorithm's objective correctly rank the closest well as best?
                      Reported with full tie context: how many wells tie at d_min, and if wrong,
                      how many steps off was the objective's actual pick vs the true best.

Grid step on the simplex: one step changes two dyes by ±0.05 mL each
  → 1-step radius = sqrt(2)*0.05 ≈ 0.0707 mL
  → 2-step radius = sqrt(2)*0.10 ≈ 0.1414 mL
"""

import pandas as pd
import numpy as np
import pathlib
import matplotlib.pyplot as plt
import sys
sys.stdout.reconfigure(encoding="utf-8")

ROOT = pathlib.Path(r"C:\Users\owenm\OneDrive\Desktop\Master Budget Dispenser\actuator-dispenser")
BASE = ROOT / "output" / "color_matching_workflow" / "algorithm_comparison"
OUT  = ROOT / "output" / "color_matching_workflow" / "analysis"

TARGET_R, TARGET_Y, TARGET_B = 0.30, 0.20, 0.50

# Grid step size and thresholds
STEP = 0.05
D1 = np.sqrt(2) * STEP        # ≈ 0.0707 mL — within 1 grid step
D2 = np.sqrt(2) * 2 * STEP    # ≈ 0.1414 mL — within 2 grid steps
TIE_TOL = 1e-4                 # wells within this of d_min are considered tied

runs = [
    ("20251216_131032_LAB_random",  "Sobol"),
    ("20251218_092306_LAB_bayBE",   "BayBE"),
    ("20251222_082441_LAB_gradient","Gradient"),
    ("20251223_103101_LAB_convex",  "Convex"),
]

COLORS = {"Sobol": "#e377c2", "BayBE": "#1f77b4",
          "Gradient": "#2ca02c", "Convex": "#ff7f0e"}


def steps_from_d(d):
    """Convert a composition-space distance to equivalent grid steps."""
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

    # ── best by objective (lower output = closer match) ──
    best_obj_idx  = data["output"].idxmin()
    best_obj_row  = data.loc[best_obj_idx]
    best_obj_iter = int(best_obj_row["well_num"])
    best_obj_d    = best_obj_row["d_input"]

    # ── convergence speed: first iter where running-min objective == global best ──
    global_best_obj  = data["output"].min()
    data["run_min"]  = data["output"].expanding().min()
    first_found_iter = int(data.loc[(data["run_min"] <= global_best_obj + 1e-9).idxmax(), "well_num"])

    # ── first iter where a 1-step well was visited ──
    hits1_mask       = data["d_input"] <= D1 + 1e-9
    first_1step_iter = int(data.loc[hits1_mask, "well_num"].min()) if hits1_mask.any() else None

    # ── best-by-composition well (for reference) ──
    best_d_row = data.loc[data["d_input"].idxmin()]

    # ── alignment metric — with full tie accounting ──────────────────────────
    # How many wells are tied at d_min?
    tied_mask    = data["d_input"] <= d_min + TIE_TOL
    n_tied       = int(tied_mask.sum())
    # Is the objective's pick among those tied-best wells?
    obj_correct  = best_obj_d <= d_min + TIE_TOL
    # Steps off for objective's pick vs true best
    steps_obj    = steps_from_d(best_obj_d)
    steps_best   = steps_from_d(d_min)
    steps_gap    = steps_obj - steps_best  # 0 if correct, positive if wrong

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
        # metric 2 — accuracy
        "d_min_mL":         round(d_min, 4),
        "steps_off":        round(steps_best, 2),
        # metric 3 & 4 — hit density
        "n_hits_1step":     int(n_hits1),
        "pct_hits_1step":   round(100 * n_hits1 / n_total, 1),
        "n_hits_2step":     int(n_hits2),
        "pct_hits_2step":   round(100 * n_hits2 / n_total, 1),
        # metric 1 — speed
        "first_found_iter": first_found_iter,
        "pct_used_to_find": round(100 * first_found_iter / n_total, 1),
        "first_1step_iter": first_1step_iter,
        "pct_used_1step":   round(100 * first_1step_iter / n_total, 1) if first_1step_iter is not None else None,
        # metric 5 — alignment
        "obj_correct":      obj_correct,
        "n_tied_at_best":   n_tied,
        "steps_obj":        round(steps_obj, 2),
        "steps_best":       round(steps_best, 2),
        "steps_gap":        round(steps_gap, 2),
        "alignment_str":    alignment_str,
        # reference compositions
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
    s1 = (f"iter {r['first_1step_iter']} ({r['pct_used_1step']:.0f}%)"
          if r["first_1step_iter"] is not None else "NEVER")
    print(f"  1. Speed:       best-by-obj found at iter {r['first_found_iter']} "
          f"({r['pct_used_to_find']:.0f}% of budget)")
    print(f"                  first 1-step hit: {s1}")
    print(f"  2. Accuracy:    d_min = {r['d_min_mL']:.4f} mL  ~= {r['steps_off']:.2f} grid steps")
    print(f"                  best-by-composition: R={r['best_d_R']:.2f}  Y={r['best_d_Y']:.2f}  B={r['best_d_B']:.2f}")
    print(f"  3. Hit density: ≤1 step: {r['n_hits_1step']:2d}/{r['n_total']} ({r['pct_hits_1step']:.1f}%)  "
          f"≤2 steps: {r['n_hits_2step']:2d}/{r['n_total']} ({r['pct_hits_2step']:.1f}%)")
    print(f"  4. (see 3)")
    print(f"  5. Alignment:   {r['alignment_str']}")
    print(f"                  obj pick: R={r['best_obj_R']:.2f}  Y={r['best_obj_Y']:.2f}  "
          f"B={r['best_obj_B']:.2f}  (d={r['best_obj_d']:.4f} mL)")

print(f"\n{'='*72}")
print("\nSUMMARY TABLE:")
cols = ["label", "d_min_mL", "steps_off",
        "pct_hits_1step", "pct_hits_2step",
        "pct_used_to_find", "first_1step_iter",
        "obj_correct", "n_tied_at_best", "steps_gap"]
print(summary[cols].to_string(index=False))

# ── save CSVs ─────────────────────────────────────────────────────────────────
# Summary: one row per algorithm
csv_summary = OUT / "dec25_algorithm_comparison.csv"
summary.to_csv(csv_summary, index=False)
print(f"\nSummary CSV saved → {csv_summary}")

# Convergence: per-well d_input for every algorithm (wide format)
conv_df = pd.DataFrame({"well": run_dfs[list(run_dfs)[0]]["well_num"].values})
for label, data in run_dfs.items():
    conv_df[f"d_input_{label}"]   = data["d_input"].values
    conv_df[f"best_so_far_{label}"] = data["d_input"].expanding().min().values
csv_conv = OUT / "dec25_algorithm_comparison_convergence.csv"
conv_df.to_csv(csv_conv, index=False)
print(f"Convergence CSV saved → {csv_conv}")

# ── 3-panel paper figure: stacked bars (left col) + convergence (right col) ───
labels     = [r["label"] for r in results]
x          = np.arange(len(labels))
bar_colors = [COLORS[l] for l in labels]

fig = plt.figure(figsize=(13, 5), constrained_layout=True)
gs  = fig.add_gridspec(2, 2, width_ratios=[1, 1.6], hspace=0.12)

ax_acc  = fig.add_subplot(gs[0, 0])   # top-left:    d_min
ax_hit  = fig.add_subplot(gs[1, 0])   # bottom-left: % ≤1 step
ax_conv = fig.add_subplot(gs[:, 1])   # right col:   convergence (full height)

# ── panel A (top): d_min ──────────────────────────────────────────────────────
bars = ax_acc.bar(x, [r["d_min_mL"] for r in results],
                  color=bar_colors, edgecolor="k", linewidth=0.8, zorder=3)
ax_acc.axhline(D1, color="dimgrey", ls="--", lw=1.2, zorder=2,
               label=f"1 step ({D1:.3f} mL)")
ax_acc.axhline(D2, color="dimgrey", ls=":",  lw=1.2, zorder=2,
               label=f"2 steps ({D2:.3f} mL)")
for bar, r in zip(bars, results):
    cx, h = bar.get_x() + bar.get_width() / 2, bar.get_height()
    steps = int(round(r["steps_off"]))
    label_str = "exact" if steps == 0 else f"{steps} step{'s' if steps != 1 else ''}"
    ax_acc.text(cx, h + 0.005, label_str,
                ha="center", va="bottom", fontsize=9)
ax_acc.set_xticks(x)
ax_acc.set_xticklabels([])            # hide — shared x-axis, labels on bottom panel
ax_acc.set_ylabel("d_min (mL)")
ax_acc.set_ylim(0, max(r["d_min_mL"] for r in results) * 1.5)
ax_acc.set_title("A. Accuracy & hit density", fontsize=10, loc="left")
ax_acc.legend(fontsize=7.5, loc="upper right")
ax_acc.grid(axis="y", alpha=0.3, zorder=0)

# ── panel A (bottom): % wells ≤1 step ────────────────────────────────────────
bars2 = ax_hit.bar(x, [r["n_hits_1step"] for r in results],
                   color=bar_colors, edgecolor="k", linewidth=0.8, zorder=3)
n_total = results[0]["n_total"]
for bar, r in zip(bars2, results):
    cx, h = bar.get_x() + bar.get_width() / 2, bar.get_height()
    ax_hit.text(cx, h + 0.1, f"{r['n_hits_1step']}/{n_total}",
                ha="center", va="bottom", fontsize=9)
ax_hit.set_xticks(x)
ax_hit.set_xticklabels(labels, fontsize=10)
ax_hit.set_ylabel(f"Wells within 1 step (out of {n_total})")
ax_hit.set_ylim(0, max(r["n_hits_1step"] for r in results) * 1.5 + 1)
ax_hit.grid(axis="y", alpha=0.3, zorder=0)

# ── panel B: best-so-far convergence curves ───────────────────────────────────
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
ax_conv.set_xlim(1, max(len(d) for d in run_dfs.values()))

fig.suptitle(
    f"Algorithm comparison — LAB colorspace  |  Target: R={TARGET_R} Y={TARGET_Y} B={TARGET_B} mL",
    fontsize=11
)

fig_out = OUT / "dec25_algorithm_comparison.png"
fig.savefig(fig_out, dpi=150, bbox_inches="tight")
print(f"Figure saved → {fig_out}")

plt.show()
