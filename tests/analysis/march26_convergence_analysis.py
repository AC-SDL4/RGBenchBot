"""
Convergence analysis for March 2026 color-matching runs.

For each of the 5 runs (LAB, RGB, HSV, RGBN, LABN) compares:
  1. How quickly was the best well (by objective) first found?
  2. How close did we get to the known target (R=0.40, Y=0.55, B=0.05)?
  3. Hit density within 1 and 2 grid steps of target.
  4. Did the optimizer correctly identify the closest-to-target well as best?

Grid step on the simplex: one step changes two dyes by ±0.05 mL each
  → 1-step radius = sqrt(2)*0.05 ≈ 0.0707 mL
  → 2-step radius = sqrt(2)*0.10 ≈ 0.1414 mL  (or 0.1225 for diagonal moves)
We use 0.075 and 0.150 as generous thresholds to capture all 1- and 2-step
neighbours respectively, consistent with 0.05 mL grid resolution.
"""

import pandas as pd
import numpy as np
import pathlib
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

ROOT = pathlib.Path(r"C:\Users\owenm\OneDrive\Desktop\Master Budget Dispenser\actuator-dispenser")
BASE = ROOT / "output" / "color_matching_workflow" / "March_2026"
OUT  = ROOT / "output" / "uncertainty_measurement_workflow" / "lod_analysis"

TARGET_R, TARGET_Y, TARGET_B = 0.40, 0.55, 0.05

# Grid step thresholds on the simplex (changing one pair of dyes by 0.05 each)
D1 = np.sqrt(2) * 0.05   # ≈ 0.0707  — within 1 grid step
D2 = np.sqrt(2) * 0.10   # ≈ 0.1414  — within 2 grid steps

runs = [
    ("20260320_081432_LAB",                "LAB"),
    ("20260320_102831_RGB",                "RGB"),
    ("20260320_123918_HSV_No_AllWells_Photo", "HSV"),
    ("20260323_113038_RGBN",               "RGBN"),
    ("20260402_091558_LABN",               "LABN"),
]

COLORS = {"LAB": "#1f77b4", "RGB": "#ff7f0e", "HSV": "#2ca02c",
          "RGBN": "#9467bd", "LABN": "#d62728"}

# ── collect per-run stats ──────────────────────────────────────────────────────
results = []
run_dfs  = {}

for folder, label in runs:
    df = pd.read_csv(BASE / folder / "color_matching_results.csv")
    data = df[df["well"] != "Target"].copy()
    data["well_num"] = pd.to_numeric(data["well"], errors="coerce")
    data = data.dropna(subset=["well_num"]).sort_values("well_num").reset_index(drop=True)

    data["d_input"] = np.sqrt(
        (data["R_volume_ml"] - TARGET_R)**2 +
        (data["Y_volume_ml"] - TARGET_Y)**2 +
        (data["B_volume_ml"] - TARGET_B)**2
    )

    n_total    = len(data)
    d_min      = data["d_input"].min()
    n_hits1    = (data["d_input"] <= D1 + 1e-9).sum()
    n_hits2    = (data["d_input"] <= D2 + 1e-9).sum()

    # best by objective: lower output = better match
    best_obj_idx  = data["output"].idxmin()
    best_obj_row  = data.loc[best_obj_idx]
    best_obj_iter = int(best_obj_row["well_num"])
    best_obj_d    = best_obj_row["d_input"]

    # best by composition distance
    best_d_idx    = data["d_input"].idxmin()
    best_d_row    = data.loc[best_d_idx]

    # First iteration where running-minimum objective is at its global best
    global_best_obj = data["output"].min()
    data["run_min_obj"] = data["output"].expanding().min()
    first_found_mask = data["run_min_obj"] <= global_best_obj + 1e-9
    first_found_iter = int(data.loc[first_found_mask.idxmax(), "well_num"])

    # First iteration where a 1-step-or-closer well was visited
    hits1_mask = data["d_input"] <= D1 + 1e-9
    first_1step_iter = int(data.loc[hits1_mask, "well_num"].min()) if hits1_mask.any() else None

    # Does the objective correctly pick the closest-to-target?
    # (ties: check if best-by-obj is among the closest wells within 1e-4 of d_min)
    obj_picks_closest = best_obj_d <= d_min + 1e-4

    results.append({
        "label":           label,
        "n_total":         n_total,
        "d_min_mL":        round(d_min, 4),
        "steps_off":       round(d_min / (np.sqrt(2) * 0.05), 1),
        "n_hits_1step":    int(n_hits1),
        "pct_hits_1step":  round(100 * n_hits1 / n_total, 1),
        "n_hits_2step":    int(n_hits2),
        "pct_hits_2step":  round(100 * n_hits2 / n_total, 1),
        "best_obj_iter":   best_obj_iter,
        "first_found_iter": first_found_iter,
        "pct_used_to_find": round(100 * first_found_iter / n_total, 1),
        "first_1step_iter": first_1step_iter,
        "pct_used_1step":   round(100 * first_1step_iter / n_total, 1) if first_1step_iter is not None else None,
        "obj_picks_closest": obj_picks_closest,
        "best_obj_R":      best_obj_row["R_volume_ml"],
        "best_obj_Y":      best_obj_row["Y_volume_ml"],
        "best_obj_B":      best_obj_row["B_volume_ml"],
        "best_obj_d":      round(best_obj_d, 4),
        "best_d_R":        best_d_row["R_volume_ml"],
        "best_d_Y":        best_d_row["Y_volume_ml"],
        "best_d_B":        best_d_row["B_volume_ml"],
    })
    run_dfs[label] = data

summary = pd.DataFrame(results)

# ── print summary ──────────────────────────────────────────────────────────────
print("=" * 70)
print(f"TARGET: R={TARGET_R}  Y={TARGET_Y}  B={TARGET_B}  (sum={TARGET_R+TARGET_Y+TARGET_B:.2f} mL)")
print(f"Grid step: 0.05 mL  |  1-step d ≈ {D1:.4f} mL  |  2-step d ≈ {D2:.4f} mL")
print("=" * 70)

for r in results:
    ok = "YES ✓" if r["obj_picks_closest"] else "NO ✗"
    print(f"\n{'─'*60}")
    print(f"  {r['label']}  ({r['n_total']} wells evaluated)")
    step1_str = (f"iter {r['first_1step_iter']} / {r['n_total']}  ({r['pct_used_1step']:.1f}% of budget)"
                 if r['first_1step_iter'] is not None else "NEVER")
    print(f"  1. Speed (by objective):     best found at iter {r['first_found_iter']} / {r['n_total']}"
          f"  ({r['pct_used_to_find']}% of budget)")
    print(f"     Speed (first 1-step hit): {step1_str}")
    print(f"  2. Closest:   d_min = {r['d_min_mL']:.4f} mL  ≈ {r['steps_off']:.1f} grid steps")
    print(f"               best-by-obj: R={r['best_obj_R']:.2f}  Y={r['best_obj_Y']:.2f}"
          f"  B={r['best_obj_B']:.2f}  d={r['best_obj_d']:.4f}")
    print(f"  3. Hit density:")
    print(f"     ≤1 step (d≤{D1:.4f}): {r['n_hits_1step']:2d} / {r['n_total']} = {r['pct_hits_1step']:.1f}%")
    print(f"     ≤2 step (d≤{D2:.4f}): {r['n_hits_2step']:2d} / {r['n_total']} = {r['pct_hits_2step']:.1f}%")
    print(f"  4. Obj picks closest?  {ok}")

print(f"\n{'='*70}")
print("\nSUMMARY TABLE:")
print(summary[["label","n_total","d_min_mL",
               "n_hits_1step","pct_hits_1step","n_hits_2step","pct_hits_2step",
               "first_1step_iter","pct_used_1step",
               "first_found_iter","pct_used_to_find","obj_picks_closest"]].to_string(index=False))

# ── plot ───────────────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(16, 10))
gs  = gridspec.GridSpec(2, 3, figure=fig, hspace=0.45, wspace=0.35)

labels = [r["label"] for r in results]
x      = np.arange(len(labels))

# ── panel A: d_min per run ────────────────────────────────────────────────────
ax_a = fig.add_subplot(gs[0, 0])
bars = ax_a.bar(x, [r["d_min_mL"] for r in results],
                color=[COLORS[l] for l in labels], edgecolor="k", linewidth=0.7)
ax_a.axhline(D1, color="grey", ls="--", lw=1, label=f"1-step ({D1:.3f})")
ax_a.axhline(D2, color="grey", ls=":",  lw=1, label=f"2-step ({D2:.3f})")
ax_a.set_xticks(x); ax_a.set_xticklabels(labels)
ax_a.set_ylabel("Min composition distance (mL)")
ax_a.set_title("A. Closest well to target")
ax_a.legend(fontsize=8)
for bar, r in zip(bars, results):
    ax_a.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.003,
              f"{r['d_min_mL']:.3f}", ha="center", va="bottom", fontsize=8)

# ── panel B: hit density ──────────────────────────────────────────────────────
ax_b = fig.add_subplot(gs[0, 1])
w = 0.35
ax_b.bar(x - w/2, [r["pct_hits_1step"] for r in results], w,
         color=[COLORS[l] for l in labels], edgecolor="k", linewidth=0.7,
         label="≤1 step", alpha=0.9)
ax_b.bar(x + w/2, [r["pct_hits_2step"] for r in results], w,
         color=[COLORS[l] for l in labels], edgecolor="k", linewidth=0.7,
         label="≤2 steps", alpha=0.5, hatch="//")
ax_b.set_xticks(x); ax_b.set_xticklabels(labels)
ax_b.set_ylabel("Wells near target (%)")
ax_b.set_title("B. Hit density near target")
ax_b.legend(fontsize=8)

# ── panel C: discovery speed ─────────────────────────────────────────────────
ax_c = fig.add_subplot(gs[0, 2])
ax_c.bar(x, [r["pct_used_to_find"] for r in results],
         color=[COLORS[l] for l in labels], edgecolor="k", linewidth=0.7)
ax_c.set_xticks(x); ax_c.set_xticklabels(labels)
ax_c.set_ylabel("% of budget used to find best")
ax_c.set_title("C. Discovery speed")
ax_c.set_ylim(0, 105)
for bar, r in zip(ax_c.patches, results):
    ax_c.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
              f"iter {r['first_found_iter']}", ha="center", va="bottom", fontsize=8)

# ── panels D–H: convergence curves per run ───────────────────────────────────
for i, (label, data) in enumerate(run_dfs.items()):
    row, col = divmod(i, 3)
    ax = fig.add_subplot(gs[1, col] if row == 0 else gs[1, col])
    # only 2 slots on row 1 (positions 0,1,2) → use lower row for first 3
    # actually gs[1, 0..2] covers the full lower row; we have 5 runs so:
    #   run 0,1,2 → gs[1,0], gs[1,1], gs[1,2] — but we only have 3 cols
    #   runs 3,4 would overflow; put them on row 0 col 1 and 2? No, those are taken.
    # Restructure: use a separate figure for convergence curves

# ── re-do: separate convergence figure ───────────────────────────────────────
plt.close(fig)

fig, axes = plt.subplots(2, 3, figsize=(16, 9), constrained_layout=True)
axes_flat = axes.flatten()
axes_flat[-1].set_visible(False)  # hide 6th panel (only 5 runs)

for i, (label, data) in enumerate(run_dfs.items()):
    ax = axes_flat[i]
    color = COLORS[label]

    # composition distance over iterations
    ax2 = ax.twinx()
    ax2.plot(data["well_num"], data["d_input"], color="lightcoral",
             alpha=0.5, lw=1, label="d_input (right)")
    ax2.axhline(D1, color="lightcoral", ls="--", lw=0.8, alpha=0.7)
    ax2.set_ylabel("Comp. distance (mL)", color="lightcoral", fontsize=8)
    ax2.tick_params(axis="y", labelcolor="lightcoral")

    # running best objective
    ax.plot(data["well_num"], data["output"], color=color, alpha=0.35,
            lw=1, label="objective")
    ax.plot(data["well_num"], data["run_min_obj"], color=color,
            lw=2, label="running best")

    # mark when best was first found
    r = next(r2 for r2 in results if r2["label"] == label)
    ax.axvline(r["first_found_iter"], color="k", ls=":", lw=1.2)
    ax.text(r["first_found_iter"] + 0.3,
            ax.get_ylim()[1] if ax.get_ylim()[1] != 0 else 1,
            f"iter {r['first_found_iter']}", fontsize=7, va="top")

    ax.set_xlabel("Well # (iteration order)")
    ax.set_ylabel("Objective value", color=color)
    ax.tick_params(axis="y", labelcolor=color)
    picks = "✓ correct" if r["obj_picks_closest"] else "✗ wrong pick"
    ax.set_title(f"{label}  |  d_min={r['d_min_mL']:.3f} mL  |  {picks}", fontsize=9)

fig.suptitle("March 2026 — Optimizer convergence & composition-space accuracy", fontsize=12)

out_path = OUT / "march26_convergence.png"
fig.savefig(out_path, dpi=150, bbox_inches="tight")
print(f"\nFigure saved → {out_path}")

# ── summary bar chart figure ──────────────────────────────────────────────────
fig2, axes2 = plt.subplots(1, 3, figsize=(14, 4.5), constrained_layout=True)

# A — closest distance
ax = axes2[0]
bars = ax.bar(labels, [r["d_min_mL"] for r in results],
              color=[COLORS[l] for l in labels], edgecolor="k", linewidth=0.8)
ax.axhline(D1, color="dimgrey", ls="--", lw=1.2, label=f"1-step threshold ({D1:.3f})")
ax.axhline(D2, color="dimgrey", ls=":",  lw=1.2, label=f"2-step threshold ({D2:.3f})")
for bar, r in zip(bars, results):
    marker = " ✓" if r["obj_picks_closest"] else " ✗"
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.003,
            f"{r['d_min_mL']:.3f}{marker}", ha="center", va="bottom", fontsize=9)
ax.set_ylabel("Min composition distance (mL)")
ax.set_title("A. Closest well found\n(✓ = obj correctly identified it)")
ax.legend(fontsize=8)
ax.set_ylim(0, max(r["d_min_mL"] for r in results) * 1.25)

# B — hit density
ax = axes2[1]
w = 0.35
ax.bar(x - w/2, [r["pct_hits_1step"] for r in results], w,
       color=[COLORS[l] for l in labels], edgecolor="k", linewidth=0.8,
       label="≤1 step", alpha=0.9)
ax.bar(x + w/2, [r["pct_hits_2step"] for r in results], w,
       color=[COLORS[l] for l in labels], edgecolor="k", linewidth=0.8,
       label="≤2 steps", alpha=0.5, hatch="//")
ax.set_xticks(x); ax.set_xticklabels(labels)
ax.set_ylabel("Wells within threshold (%)")
ax.set_title("B. Hit density near target")
ax.legend(fontsize=8)

# C — discovery speed (two series: by objective and by first 1-step hit)
ax = axes2[2]
w = 0.35
pct_obj   = [r["pct_used_to_find"] for r in results]
pct_1step = [r["pct_used_1step"] if r["pct_used_1step"] is not None else 100 for r in results]
bars_obj   = ax.bar(x - w/2, pct_obj,   w, color=[COLORS[l] for l in labels],
                    edgecolor="k", linewidth=0.8, label="By objective", alpha=0.9)
bars_1step = ax.bar(x + w/2, pct_1step, w, color=[COLORS[l] for l in labels],
                    edgecolor="k", linewidth=0.8, label="First 1-step hit", alpha=0.5, hatch="//")
for bar, r in zip(bars_obj, results):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1.5,
            f"{r['first_found_iter']}", ha="center", va="bottom", fontsize=8)
for bar, r in zip(bars_1step, results):
    label_txt = str(r["first_1step_iter"]) if r["first_1step_iter"] is not None else "N/A"
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1.5,
            label_txt, ha="center", va="bottom", fontsize=8)
ax.set_xticks(x); ax.set_xticklabels(labels)
ax.set_ylabel("Budget used (%)")
ax.set_title("C. Discovery speed")
ax.set_ylim(0, 115)
ax.legend(fontsize=8)

fig2.suptitle("March 2026 color-matching — Composition-space evaluation", fontsize=12)
out_path2 = OUT / "march26_summary_bars.png"
fig2.savefig(out_path2, dpi=150, bbox_inches="tight")
print(f"Summary bars saved → {out_path2}")
