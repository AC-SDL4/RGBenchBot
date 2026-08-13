"""
Combined LoD Analysis: BEST (Feb 24) + Mar 13 experiments
==========================================================
Both experiments use the same darkest ink stock, so sensitivity coefficients
(channel units per mL of dye) are directly comparable and can be estimated
from the pooled 48-well dataset.

Pooling gives 7-8 distinct compositions vs 4 in any single experiment,
producing a better-conditioned sensitivity regression.

sigma_within (noise) is computed from the 6 within-well replicates across
all 48 wells.

Known issues flagged in output:
  - Replicate 1 outlier (camera warm-up): computed with and without rep 1
  - C_ref for C' uses joint dataset well means (not per-experiment)
  - Sensitivity regression uses intended compositions, not measured volumes

Rep 1 (first photo of each well) is excluded throughout: camera auto-exposure
has not yet settled at rep 1, causing 3-4x inflated noise. All sigma_within,
well means, and sensitivity regression use reps 2-6 only.

Outputs to output/uncertainty_measurement_workflow/lod_analysis/:
    combined_raw.csv              -- pooled raw measurements (48 wells x 6 reps)
    composition_map.csv           -- all 8 compositions
    sensitivity_coefficients.csv  -- regression fit on 48 well means (reps 2-6)
    lod_summary.csv               -- LoD = sigma / |sensitivity|
    lod_heatmap.png
    lod_ranking.png
    rep1_effect.csv               -- documents how much rep1 inflates sigma
"""

from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[3]
UMW  = ROOT / "output" / "uncertainty_measurement_workflow"
OUT  = UMW / "lod_analysis"
OUT.mkdir(parents=True, exist_ok=True)

SOURCES = [
    ("BEST_20260224_123236_automated_darkest_most_yellow_7_1_1",   "BEST"),
    ("20260313_110043_automated_6_2_1",                             "Mar13"),
]

RAW_CHANNELS = ['RGB_R', 'RGB_G', 'RGB_B',
                'LAB_L', 'LAB_A', 'LAB_B',
                'HSV_H', 'HSV_S', 'HSV_V']
ALL_CHANNELS = RAW_CHANNELS
DYES         = ['v_R', 'v_Y', 'v_B']

MIN_SENSITIVITY = 0.05


# -----------------------------------------------------------------------
# Load and pool raw data
# -----------------------------------------------------------------------
frames = []
well_offset = 0

for folder, tag in SOURCES:
    raw_csv  = UMW / folder / "uncertainty_measurements_raw.csv"
    comp_csv = UMW / folder / "composition_map.csv"
    raw  = pd.read_csv(raw_csv)
    comp = pd.read_csv(comp_csv)

    # Merge composition onto each row
    raw = raw.merge(comp[['group_id', 'v_R', 'v_Y', 'v_B']], on='group_id', how='left')
    raw['source']     = tag
    # Re-index wells to avoid collision between experiments
    raw['well_global'] = raw['well_index'] + well_offset
    well_offset += raw['well_index'].nunique()
    frames.append(raw)

combined = pd.concat(frames, ignore_index=True)

# Save combined raw
combined.to_csv(OUT / "combined_raw.csv", index=False)
print(f"Combined dataset: {len(combined)} rows, {combined['well_global'].nunique()} wells")

# Composition map (all unique)
comp_all = combined[['v_R','v_Y','v_B','source']].drop_duplicates().sort_values(['v_R','v_Y','v_B'])
comp_all.to_csv(OUT / "composition_map.csv", index=False)
print(f"Unique compositions: {len(comp_all)}")

# -----------------------------------------------------------------------
# Exclude rep 1 throughout: camera auto-exposure not yet settled at rep 1.
# All sigma, well means, and regression use reps 2-6 only.
# Rep-1 effect is documented separately for reference.
# -----------------------------------------------------------------------
clean = combined[combined['replicate_id'] != 1].copy()

# Rep-1 effect report (informational only)
all_reps_sigma = {}
for ch in RAW_CHANNELS:
    all_reps_sigma[ch] = combined.groupby('well_global')[ch].std(ddof=1).mean()

# sigma_within from reps 2-6
sigma = {}
for ch in RAW_CHANNELS:
    sigma[ch] = clean.groupby('well_global')[ch].std(ddof=1).mean()

# Rep-1 effect report
rep1_rows = []
for ch in ALL_CHANNELS:
    if ch in all_reps_sigma and ch in sigma:
        rep1_rows.append({
            'channel': ch,
            'sigma_all_reps': all_reps_sigma[ch],
            'sigma_excl_rep1': sigma[ch],
            'inflation_factor': all_reps_sigma[ch] / sigma[ch] if sigma[ch] > 0 else np.nan,
        })
rep1_df = pd.DataFrame(rep1_rows).sort_values('inflation_factor', ascending=False)
rep1_df.to_csv(OUT / "rep1_effect.csv", index=False)
print(f"\nTop 5 channels most inflated by rep1:")
print(rep1_df.head().to_string(index=False))

# -----------------------------------------------------------------------
# Sensitivity regression: well means from reps 2-6
# -----------------------------------------------------------------------
well_df = clean.groupby('well_global')[ALL_CHANNELS + ['v_R', 'v_Y', 'v_B']].mean()
X = well_df[['v_R', 'v_Y', 'v_B']].values

coef_rows = []
for ch in ALL_CHANNELS:
    if ch not in well_df.columns:
        continue
    y = well_df[ch].values
    mask = ~np.isnan(y)
    if mask.sum() < 8:
        continue
    reg = LinearRegression(fit_intercept=True).fit(X[mask], y[mask])
    r2  = reg.score(X[mask], y[mask])
    coef_rows.append({
        'channel':    ch,
        'channel_type': 'raw' if ch in RAW_CHANNELS else 'normalized',
        'coef_v_R':   reg.coef_[0],
        'coef_v_Y':   reg.coef_[1],
        'coef_v_B':   reg.coef_[2],
        'intercept':  reg.intercept_,
        'r2':         r2,
    })

coef_df = pd.DataFrame(coef_rows)
coef_df.to_csv(OUT / "sensitivity_coefficients.csv", index=False)
print(f"\nSensitivity R² range: {coef_df['r2'].min():.3f} – {coef_df['r2'].max():.3f}")
print(coef_df[['channel','r2','coef_v_R','coef_v_Y','coef_v_B']].to_string(index=False))

# -----------------------------------------------------------------------
# LoD: sigma_within / |sensitivity|  (both all-reps and excl-rep1)
# -----------------------------------------------------------------------
coef_idx = coef_df.set_index('channel')
lod_rows = []

for ch in ALL_CHANNELS:
    if ch not in sigma or ch not in coef_idx.index:
        continue
    ch_type = 'raw' if ch in RAW_CHANNELS else 'normalized'
    for dye, col in zip(DYES, ['coef_v_R', 'coef_v_Y', 'coef_v_B']):
        coef      = coef_idx.loc[ch, col]
        abs_coef  = abs(coef)
        lod_no1   = sigma[ch]                / abs_coef if abs_coef >= MIN_SENSITIVITY else np.nan
        lod_all   = all_reps_sigma.get(ch, np.nan) / abs_coef if abs_coef >= MIN_SENSITIVITY else np.nan
        lod_rows.append({
            'channel':          ch,
            'channel_type':     ch_type,
            'dye':              dye,
            'sigma_all_reps':   all_reps_sigma.get(ch, np.nan),
            'sigma_excl_rep1':  sigma[ch],
            'sensitivity':      coef,
            'abs_sensitivity':  abs_coef,
            'r2':               coef_idx.loc[ch, 'r2'],
            'lod_all_reps':     lod_all,
            'lod_excl_rep1':    lod_no1,
        })

lod_df = pd.DataFrame(lod_rows)
lod_df.to_csv(OUT / "lod_summary.csv", index=False)
print(f"\nSaved: {OUT / 'lod_summary.csv'}")

# -----------------------------------------------------------------------
# Plots
# -----------------------------------------------------------------------
dye_labels = {'v_R': 'Red dye', 'v_Y': 'Yellow dye', 'v_B': 'Blue dye'}

def make_pivot(metric):
    p = lod_df.pivot_table(index='channel', columns='dye', values=metric)
    return p[DYES] if set(DYES).issubset(p.columns) else p

# Side-by-side heatmap: all reps  vs  reps 2-6
# Channel order fixed from excl-rep1 ranking so rows align between panels
def sorted_pivot(metric):
    piv = make_pivot(metric)
    raw_p = piv.loc[[c for c in RAW_CHANNELS if c in piv.index]].copy()
    ref   = make_pivot('lod_excl_rep1')
    raw_ref = ref.loc[[c for c in RAW_CHANNELS if c in ref.index]]
    return raw_p.loc[raw_ref.mean(axis=1).sort_values().index]

piv_all = sorted_pivot('lod_all_reps')
piv_no1 = sorted_pivot('lod_excl_rep1')
vmax = np.nanpercentile(
    np.concatenate([piv_all.values.flatten(), piv_no1.values.flatten()]), 85)

fig, axes = plt.subplots(1, 2, figsize=(13, 9))
for ax, piv, title in [
    (axes[0], piv_all, 'All 6 reps\n(real-workflow conditions)'),
    (axes[1], piv_no1, 'Reps 2-6 only\n(rep1 outlier excluded)'),
]:
    data = piv.values.astype(float)
    im = ax.imshow(data, aspect='auto', cmap='YlOrRd_r', vmin=0, vmax=vmax)
    ax.set_xticks(range(3))
    ax.set_xticklabels([dye_labels[d] for d in DYES], fontsize=9)
    ax.set_yticks(range(len(piv.index)))
    ax.set_yticklabels(piv.index, fontsize=9)
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            v = data[i, j]
            if np.isnan(v):
                ax.text(j, i, 'n/s', ha='center', va='center', fontsize=7, color='gray')
            else:
                color = 'white' if v < vmax * 0.3 else 'black'
                ax.text(j, i, f'{v:.4f}', ha='center', va='center', fontsize=7, color=color)
    plt.colorbar(im, ax=ax, label='LoD (mL) - lower = better', shrink=0.75)
    ax.set_title(title, fontsize=10, pad=8)
fig.suptitle('Combined BEST + Mar13 — Limit of Detection\n'
             'Both panels use same colour scale and row order',
             fontsize=11)
plt.tight_layout()
fig.savefig(OUT / 'lod_heatmap.png', dpi=150)
plt.close(fig)
print(f"Saved: {OUT / 'lod_heatmap.png'}")

# Bar chart: excl-rep1 LoD, all channels ranked per dye
fig, axes = plt.subplots(1, 3, figsize=(16, 6))
for ax, dye in zip(axes, DYES):
    sub = lod_df[lod_df.dye == dye].dropna(subset=['lod_all_reps']).sort_values('lod_all_reps')
    ax.bar(range(len(sub)), sub['lod_all_reps'], color='#3b82f6',
           edgecolor='black', linewidth=0.5)
    ax.set_xticks(range(len(sub)))
    ax.set_xticklabels(sub['channel'], rotation=45, ha='right', fontsize=8)
    ax.set_ylabel('LoD (mL)')
    ax.set_ylim(0, 0.05)
    ax.set_title(f"{dye_labels[dye]}\nBest: {sub.iloc[0]['channel']} ({sub.iloc[0]['lod_all_reps']:.4f} mL)")
    ax.grid(axis='y', ls='--', alpha=0.4)
    for i, (_, row) in enumerate(sub.head(3).iterrows()):
        y = min(row['lod_all_reps'], 0.049)
        ax.text(i, y * 1.03,
                f"{row['lod_all_reps']:.4f}", ha='center', va='bottom', fontsize=7)

fig.suptitle('LoD ranking — Combined BEST + Mar13 (all 6 reps, real-workflow)\n'
             'Sensitivity from 48-well joint regression', fontsize=10)
plt.tight_layout()
fig.savefig(OUT / 'lod_ranking.png', dpi=150)
plt.close(fig)
print(f"Saved: {OUT / 'lod_ranking.png'}")

# -----------------------------------------------------------------------
# Console summary
# -----------------------------------------------------------------------
print('\n=== BEST CHANNEL PER DYE (all reps — real workflow) ===')
for dye in DYES:
    sub = lod_df[lod_df.dye == dye].dropna(subset=['lod_all_reps']).sort_values('lod_all_reps')
    print(f'\n  {dye_labels[dye]}:')
    for i, (_, row) in enumerate(sub.head(5).iterrows()):
        tag = 'raw' if row['channel_type'] == 'raw' else 'norm'
        print(f"    #{i+1}  {row['channel']:<6} [{tag}]  "
              f"LoD(all)={row['lod_all_reps']:.5f}  LoD(no-rep1)={row['lod_excl_rep1']:.5f} mL  "
              f"R2={row['r2']:.3f}")

print('\nKnown caveats:')
print('  - Sensitivity from intended compositions (not measured dispensed volumes)')
print('  - C_ref computed jointly; would differ if computed per-experiment')
print('  - Rep1 excluded above; see rep1_effect.csv for inflation factors')
print('\nDone.')
