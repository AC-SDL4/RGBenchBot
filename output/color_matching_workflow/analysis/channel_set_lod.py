"""
Channel-Set LoD Analysis
========================
Compares complete 3-channel "sets" (e.g., all of LAB, all of HSV, all of RGB,
normalised equivalents) for jointly estimating all 3 dye volumes.

Method  (GLS Fisher information):
  For a set of k channels with k×3 sensitivity matrix S and independent noise
  Σ = diag(σ²), the GLS estimator covariance is:
      Cov(v̂) = (Sᵀ Σ⁻¹ S)⁻¹
  LoD_j = √Cov(v̂)[j,j]  — uncertainty (mL) in estimating dye j using the
  full channel set simultaneously.

Sets evaluated:
  RGB : RGB_R, RGB_G, RGB_B
  LAB : LAB_L, LAB_A, LAB_B
  HSV : HSV_H, HSV_S, HSV_V

Reads:
  output/uncertainty_measurement_workflow/lod_analysis/lod_summary.csv
Writes to same folder:
  channel_set_lod.csv
  channel_set_lod.png
"""

from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[3]
SRC  = ROOT / "output" / "uncertainty_measurement_workflow" / "lod_analysis"

DYES       = ['v_R', 'v_Y', 'v_B']
DYE_LABELS = {'v_R': 'Red', 'v_Y': 'Yellow', 'v_B': 'Blue'}
DYE_COLORS = {'v_R': '#ef4444', 'v_Y': '#ca8a04', 'v_B': '#3b82f6'}

SETS = {
    "RGB": ["RGB_R", "RGB_G", "RGB_B"],
    "LAB": ["LAB_L", "LAB_A", "LAB_B"],
    "HSV": ["HSV_H", "HSV_S", "HSV_V"],
}
RAW_CHANNELS = ["RGB_R", "RGB_G", "RGB_B", "LAB_L", "LAB_A", "LAB_B", "HSV_H", "HSV_S", "HSV_V"]

# -----------------------------------------------------------------------
# Load per-channel sigma and sensitivity coefficients
# -----------------------------------------------------------------------
lod_df = pd.read_csv(SRC / "lod_summary.csv")

# Pivot to one row per channel with all dye coefficients and sigmas
ch_data = {}
for ch, grp in lod_df.groupby("channel"):
    r0 = grp.iloc[0]
    coefs = {r['dye']: r['sensitivity'] for _, r in grp.iterrows()}
    ch_data[ch] = {
        'sigma_all': r0['sigma_all_reps'],
        'sigma_no1': r0['sigma_excl_rep1'],
        'coef_v_R':  coefs.get('v_R', np.nan),
        'coef_v_Y':  coefs.get('v_Y', np.nan),
        'coef_v_B':  coefs.get('v_B', np.nan),
    }

# Compute sigma_proc (between-well within-group noise) for each raw channel
combined_raw = pd.read_csv(SRC / "combined_raw.csv")
clean_raw = combined_raw[combined_raw['replicate_id'] != 1]
well_means = clean_raw.groupby(['source', 'group_id', 'well_global'])[RAW_CHANNELS].mean()
sigma_proc_vals = well_means.groupby(['source', 'group_id'])[RAW_CHANNELS].std(ddof=1).mean().to_dict()
for ch in ch_data:
    ch_data[ch]['sigma_proc'] = sigma_proc_vals.get(ch, np.nan)


def multivariate_lod(channels: list[str], sigma_key: str = 'sigma_all') -> dict:
    """
    Compute per-dye LoD for a channel set via GLS Fisher information.
    Returns dict with 'v_R', 'v_Y', 'v_B' LoDs, 'cond', 'note'.
    """
    k = len(channels)
    S      = np.zeros((k, 3))
    sigmas = np.zeros(k)

    for i, ch in enumerate(channels):
        d = ch_data[ch]
        S[i, 0] = d['coef_v_R']
        S[i, 1] = d['coef_v_Y']
        S[i, 2] = d['coef_v_B']
        sigmas[i] = d[sigma_key]

    Sigma_inv = np.diag(1.0 / sigmas ** 2)
    FI  = S.T @ Sigma_inv @ S          # 3×3 Fisher information matrix
    cond = float(np.linalg.cond(FI))

    note = ''
    if cond > 1e8:
        note = f'ill-conditioned (κ={cond:.1e})'
        Cov = np.linalg.pinv(FI)       # pseudo-inverse as fallback
    else:
        try:
            Cov = np.linalg.inv(FI)
        except np.linalg.LinAlgError:
            note = 'singular'
            return {d: np.nan for d in DYES} | {'cond': cond, 'note': note}

    return ({dye: float(np.sqrt(max(Cov[i, i], 0)))
             for i, dye in enumerate(DYES)}
            | {'cond': cond, 'note': note})


# -----------------------------------------------------------------------
# Run for both sigma conditions
# -----------------------------------------------------------------------
rows = []
for set_name, channels in SETS.items():
    for sigma_key, label in [('sigma_no1', 'camera'), ('sigma_proc', 'practical')]:
        res = multivariate_lod(channels, sigma_key)
        lods = [res.get(d, np.nan) for d in DYES]
        geomean = float(np.exp(np.nanmean(np.log(np.abs(lods)))))
        rows.append({
            'set':           set_name,
            'channels':      ', '.join(channels),
            'condition':     label,
            'lod_v_R':       res.get('v_R', np.nan),
            'lod_v_Y':       res.get('v_Y', np.nan),
            'lod_v_B':       res.get('v_B', np.nan),
            'max_lod':       float(np.nanmax(lods)),
            'geomean_lod':   geomean,
            'cond_number':   res.get('cond', np.nan),
            'note':          res.get('note', ''),
        })

results = pd.DataFrame(rows)
results.to_csv(SRC / "channel_set_lod.csv", index=False)

# -----------------------------------------------------------------------
# Console summary
# -----------------------------------------------------------------------
print("\n=== CHANNEL SET MULTIVARIATE LoD (camera noise, reps 2-6) ===")
print(f"{'Set':<12} {'Red':>8} {'Yellow':>8} {'Blue':>8} {'max':>8} {'geomean':>8}  Note")
print("-" * 65)
for _, row in results[results.condition == 'camera'].sort_values('max_lod').iterrows():
    flag = f"  ⚠ {row['note']}" if row['note'] else ''
    print(f"  {row['set']:<10} "
          f"{row['lod_v_R']:>8.4f} {row['lod_v_Y']:>8.4f} {row['lod_v_B']:>8.4f} "
          f"{row['max_lod']:>8.4f} {row['geomean_lod']:>8.4f}{flag}")

print("\n=== CHANNEL SET MULTIVARIATE LoD (practical / process noise) ===")
print(f"{'Set':<12} {'Red':>8} {'Yellow':>8} {'Blue':>8} {'max':>8} {'geomean':>8}  Note")
print("-" * 65)
for _, row in results[results.condition == 'practical'].sort_values('max_lod').iterrows():
    flag = f"  ⚠ {row['note']}" if row['note'] else ''
    print(f"  {row['set']:<10} "
          f"{row['lod_v_R']:>8.4f} {row['lod_v_Y']:>8.4f} {row['lod_v_B']:>8.4f} "
          f"{row['max_lod']:>8.4f} {row['geomean_lod']:>8.4f}{flag}")

# -----------------------------------------------------------------------
# Plots
# -----------------------------------------------------------------------
set_order = (results[results.condition == 'camera']
             .sort_values('max_lod')['set'].tolist())

fig, axes = plt.subplots(1, 2, figsize=(12, 5))
for ax, condition, title in [
    (axes[0], 'camera',    'Camera noise (reps 2–6, σ_meas)'),
    (axes[1], 'practical', 'Process / well noise (σ_proc)'),
]:
    sub = (results[results.condition == condition]
           .set_index('set').loc[set_order].reset_index())
    x     = np.arange(len(sub))
    width = 0.25

    for k, dye in enumerate(DYES):
        col  = f'lod_{dye}'
        lods = sub[col].values
        bars = ax.bar(x + (k - 1) * width, lods, width,
                      label=DYE_LABELS[dye],
                      color=DYE_COLORS[dye],
                      edgecolor='black', linewidth=0.5, alpha=0.85)
        for bar, val in zip(bars, lods):
            if not np.isnan(val):
                ax.text(bar.get_x() + bar.get_width() / 2,
                        bar.get_height() + 0.0003,
                        f'{val:.3f}', ha='center', va='bottom',
                        fontsize=6.5, rotation=90)

    # Mark ill-conditioned sets
    for i, (_, row) in enumerate(sub.iterrows()):
        if row['note']:
            ax.text(i, ax.get_ylim()[1] * 0.88, '⚠', ha='center',
                    fontsize=11, color='#6b7280')

    ax.set_xticks(x)
    ax.set_xticklabels(sub['set'], fontsize=10)
    ax.set_ylabel('LoD (mL)  — lower is better')
    ax.set_title(title, fontsize=10)
    ax.set_ylim(bottom=0)
    ax.grid(axis='y', ls='--', alpha=0.4)
    ax.legend(fontsize=9, loc='upper left')

fig.suptitle(
    'Multivariate LoD by channel set — Combined BEST + Mar13 (48 wells)\n'
    r'$\mathrm{Cov}(\hat{v}) = (S^\top \Sigma^{-1} S)^{-1}$'
    '   Left: camera noise   Right: process/well noise',
    fontsize=10
)
plt.tight_layout()
fig.savefig(SRC / 'channel_set_lod.png', dpi=150)
plt.close(fig)
print(f"\nSaved: {SRC / 'channel_set_lod.png'}")

# -----------------------------------------------------------------------
# Also print sensitivity matrices for debugging
# -----------------------------------------------------------------------
print("\n=== SENSITIVITY MATRICES per set ===")
for set_name, channels in SETS.items():
    print(f"\n{set_name}: {channels}")
    S = np.array([[ch_data[ch]['coef_v_R'],
                   ch_data[ch]['coef_v_Y'],
                   ch_data[ch]['coef_v_B']] for ch in channels])
    df_s = pd.DataFrame(S, index=channels, columns=['coef_v_R', 'coef_v_Y', 'coef_v_B'])
    print(df_s.to_string(float_format='{:8.4f}'.format))
    print(f"  cond(S) = {np.linalg.cond(S):.2e}")

print("\nDone.")
