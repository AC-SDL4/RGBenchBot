import pandas as pd, numpy as np, pathlib

ROOT = pathlib.Path(r"C:\Users\owenm\OneDrive\Desktop\Master Budget Dispenser\actuator-dispenser")
base = ROOT / "output" / "color_matching_workflow" / "March_2026"

TARGET_R, TARGET_Y, TARGET_B = 0.40, 0.55, 0.05
total = TARGET_R + TARGET_Y + TARGET_B
print(f"Target: R={TARGET_R}  Y={TARGET_Y}  B={TARGET_B}  sum={total:.2f} mL")
print(f"Achievable (sums to 1.0 mL, no water needed): {'YES' if abs(total-1.0)<0.001 else 'NO'}")

runs = [
    ("20260320_081432_LAB",               "LAB"),
    ("20260320_102831_RGB",               "RGB"),
    ("20260320_123918_HSV_No_AllWells_Photo", "HSV"),
    ("20260323_113038_RGBN",              "RGBN"),
    ("20260402_091558_LABN",              "LABN"),
]

for folder, label in runs:
    df   = pd.read_csv(base / folder / "color_matching_results.csv")
    data = df[df["well"] != "Target"].copy()
    data["d_input"] = np.sqrt(
        (data["R_volume_ml"] - TARGET_R)**2 +
        (data["Y_volume_ml"] - TARGET_Y)**2 +
        (data["B_volume_ml"] - TARGET_B)**2)
    best_c = data.loc[data["d_input"].idxmin()]
    best_o = data.loc[data["output"].idxmin()]
    print()
    print(label)
    print(f"  closest to target:  well={best_c['well']:<3}  R={best_c['R_volume_ml']:.2f}  Y={best_c['Y_volume_ml']:.2f}  B={best_c['B_volume_ml']:.2f}  d={best_c['d_input']:.4f} mL")
    print(f"  best by objective:  well={best_o['well']:<3}  R={best_o['R_volume_ml']:.2f}  Y={best_o['Y_volume_ml']:.2f}  B={best_o['B_volume_ml']:.2f}  d={best_o['d_input']:.4f} mL  obj={best_o['output']:.4f}")
    print(f"  top 5 by comp distance:")
    for _, r in data.sort_values("d_input").head(5).iterrows():
        print(f"    well={r['well']:<3}  R={r['R_volume_ml']:.2f}  Y={r['Y_volume_ml']:.2f}  B={r['B_volume_ml']:.2f}  d={r['d_input']:.4f}  obj={r['output']:.4f}")
