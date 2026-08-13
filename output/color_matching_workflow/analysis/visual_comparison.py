"""
Visual comparison: target vs closest well (optimizer pick vs composition-space pick).

For each dataset and colorspace, shows:
  Row 1 (obj pick):  the well the optimizer ranked as best (lowest objective)
  Row 2 (comp pick): the well closest to the target in composition space (d_input)

Generates one figure per dataset.
"""

import pandas as pd
import numpy as np
import pathlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from PIL import Image
import sys
sys.stdout.reconfigure(encoding="utf-8")

ROOT = pathlib.Path(r"C:\Users\owenm\OneDrive\Desktop\Master Budget Dispenser\actuator-dispenser")
OUT  = ROOT / "output" / "color_matching_workflow" / "analysis"

STEP = 0.05

datasets = [
    {
        "name":   "Nov–Dec 2025 (Set 3)",
        "target": (0.50, 0.25, 0.25),
        "base":   ROOT / "output" / "color_matching_workflow" / "colorspace_comparison",
        "runs":   [
            ("20251128_094057__LAB", "LAB"),
            ("20251201_071333__RGB", "RGB"),
            ("20251203_144121__HSV", "HSV"),
        ],
        "out": OUT / "visual_comparison_nov_dec25.png",
    },
    {
        "name":   "March 2026",
        "target": (0.40, 0.55, 0.05),
        "base":   ROOT / "output" / "color_matching_workflow" / "Color_Matching_BO_March2026",
        "runs":   [
            ("20260320_081432_LAB",                  "LAB"),
            ("20260320_102831_RGB",                  "RGB"),
            ("20260320_123918_HSV_No_AllWells_Photo", "HSV"),
        ],
        "out": OUT / "visual_comparison_mar26.png",
    },
]


def find_image(crops_dir, stem):
    """Find an image by stem, tolerating an optional colorspace suffix."""
    # Try exact name first, then any file starting with the stem
    exact = crops_dir / f"{stem}.jpg"
    if exact.exists():
        return Image.open(exact)
    matches = list(crops_dir.glob(f"{stem}_*.jpg"))
    if matches:
        return Image.open(matches[0])
    raise FileNotFoundError(f"No image matching '{stem}[_*].jpg' in {crops_dir}")


def load_well_image(crops_dir, well_num):
    return find_image(crops_dir, f"center_crop_well_plateexperiment_{well_num}")


def load_target_image(crops_dir):
    return find_image(crops_dir, "center_crop_well_platetarget_sample")


def d_input(row, TR, TY, TB):
    return np.sqrt((row["R_volume_ml"] - TR)**2 +
                   (row["Y_volume_ml"] - TY)**2 +
                   (row["B_volume_ml"] - TB)**2)


def steps(d):
    return d / (np.sqrt(2) * STEP)


for ds in datasets:
    TR, TY, TB = ds["target"]
    n_cs = len(ds["runs"])

    # ── gather per-colorspace picks ───────────────────────────────────────────
    picks = []
    for folder, label in ds["runs"]:
        run_dir   = ds["base"] / folder
        crops_dir = run_dir / "center_crops"
        df = pd.read_csv(run_dir / "color_matching_results.csv")
        data = df[df["well"] != "Target"].copy()
        data["well_num"] = pd.to_numeric(data["well"], errors="coerce")
        data = data.dropna(subset=["well_num"]).sort_values("well_num").reset_index(drop=True)
        data["d_input"] = data.apply(lambda r: d_input(r, TR, TY, TB), axis=1)

        # objective pick (lower = better)
        obj_row  = data.loc[data["output"].idxmin()]
        obj_well = int(obj_row["well_num"])
        obj_d    = obj_row["d_input"]

        # composition-space pick
        comp_row  = data.loc[data["d_input"].idxmin()]
        comp_well = int(comp_row["well_num"])
        comp_d    = comp_row["d_input"]

        same = (obj_well == comp_well)

        picks.append({
            "label":      label,
            "crops_dir":  crops_dir,
            "obj_well":   obj_well,
            "obj_d":      obj_d,
            "obj_R":      obj_row["R_volume_ml"],
            "obj_Y":      obj_row["Y_volume_ml"],
            "obj_B":      obj_row["B_volume_ml"],
            "comp_well":  comp_well,
            "comp_d":     comp_d,
            "comp_R":     comp_row["R_volume_ml"],
            "comp_Y":     comp_row["Y_volume_ml"],
            "comp_B":     comp_row["B_volume_ml"],
            "same":       same,
        })

        print(f"{ds['name']} | {label}:")
        print(f"  obj pick:  well {obj_well}  R={obj_row['R_volume_ml']:.2f} Y={obj_row['Y_volume_ml']:.2f} B={obj_row['B_volume_ml']:.2f}  d={obj_d:.4f} ({steps(obj_d):.1f} steps)")
        print(f"  comp pick: well {comp_well}  R={comp_row['R_volume_ml']:.2f} Y={comp_row['Y_volume_ml']:.2f} B={comp_row['B_volume_ml']:.2f}  d={comp_d:.4f} ({steps(comp_d):.1f} steps)")
        if same:
            print(f"  (same well)")

    # ── figure: 2 rows x (1 target + n_cs colorspaces) ───────────────────────
    # Row 0: optimizer picks  |  Row 1: composition picks
    n_cols = 1 + n_cs
    fig, axes = plt.subplots(2, n_cols, figsize=(3.2 * n_cols, 7),
                             constrained_layout=True)

    target_img = load_target_image(picks[0]["crops_dir"])

    for row_idx, (row_label, pick_key, d_key, well_key, r_key, y_key, b_key) in enumerate([
        ("Optimizer pick",    "obj",  "obj_d",  "obj_well",  "obj_R",  "obj_Y",  "obj_B"),
        ("Composition-space pick", "comp", "comp_d", "comp_well", "comp_R", "comp_Y", "comp_B"),
    ]):
        # Target column
        ax = axes[row_idx, 0]
        ax.imshow(target_img)
        ax.axis("off")
        if row_idx == 0:
            ax.set_title(f"Target\nR={TR:.2f} Y={TY:.2f} B={TB:.2f}", fontsize=9, fontweight="bold")
        else:
            ax.set_title("Target\n(same)", fontsize=9)

        # Colorspace columns
        for ci, p in enumerate(picks):
            ax = axes[row_idx, ci + 1]
            well_num = p[well_key]
            d_val    = p[d_key]
            img = load_well_image(p["crops_dir"], well_num)
            ax.imshow(img)
            ax.axis("off")

            step_val = steps(d_val)
            step_str = "exact" if step_val < 0.01 else f"{step_val:.1f} steps"
            same_marker = " ✓" if p["same"] else ""
            ax.set_title(
                f"{p['label']} — well {well_num}{same_marker}\n"
                f"R={p[r_key]:.2f} Y={p[y_key]:.2f} B={p[b_key]:.2f}\n"
                f"d = {d_val:.3f} mL ({step_str})",
                fontsize=8
            )

        # Row label on left
        axes[row_idx, 0].annotate(
            row_label, xy=(-0.08, 0.5), xycoords="axes fraction",
            fontsize=9, fontweight="bold", rotation=90, va="center", ha="right"
        )

    fig.suptitle(f"{ds['name']}  |  Target: R={TR} Y={TY} B={TB} mL\n"
                 f"✓ = same well picked by both criteria", fontsize=10)

    fig.savefig(ds["out"], dpi=150, bbox_inches="tight")
    print(f"\nFigure saved → {ds['out']}\n")

plt.show()
