import pandas as pd, numpy as np

bg = pd.read_csv('output/uncertainty_measurement_workflow/noise_analysis/measurement_vs_process_uncertainty_by_group_channel.csv')
lod = pd.read_csv('output/uncertainty_measurement_workflow/lod_analysis/lod_summary.csv')

auto = bg[bg['dataset'] == 'Automated 7:1:1 primary']
man  = bg[bg['dataset'] == 'Manual 7:1:1']

# Cross-check: measurement_std averaged over 4 groups should match lod_summary sigma_all_reps
print('=== CROSS-CHECK: measurement_std vs lod_summary sigma_all_reps ===')
for ch in ['RGB_R','LAB_A','LAB_L','HSV_H']:
    lod_sigma = lod[lod['channel'] == ch]['sigma_all_reps'].iloc[0]
    bg_sigma = auto[auto['channel'] == ch]['measurement_std'].mean()
    print(f'  {ch}: lod_summary={lod_sigma:.4f}, by_group_channel mean={bg_sigma:.4f}  match={abs(lod_sigma-bg_sigma)<0.05}')

print()

# Recompute 4x3 table
merged = auto.merge(man, on=['channel','group_id'], suffixes=('_auto','_man'))
merged = merged.copy()
merged['r1_auto'] = merged['process_std_auto'] / merged['measurement_std_auto']
merged['r2_man']  = merged['process_std_man']  / merged['measurement_std_man']
merged['r3_proc'] = merged['process_std_auto'] / merged['process_std_man']
merged['r4_meas'] = merged['measurement_std_auto'] / merged['measurement_std_man']

cs_map = {
    'RGB': ['RGB_R','RGB_G','RGB_B'],
    'LAB': ['LAB_L','LAB_A','LAB_B'],
    'HSV': ['HSV_H','HSV_S','HSV_V']
}

print('=== 4x3 TABLE (median of 12 values: 3 channels x 4 groups) ===')
print(f'{"Row":<35} {"RGB":>8} {"LAB":>8} {"HSV":>8}')
print('-' * 62)
rows = [
    ('Uproc/Umeas - Automated', 'r1_auto'),
    ('Uproc/Umeas - Manual',    'r2_man'),
    ('Uproc auto/man',          'r3_proc'),
    ('Umeas auto/man',          'r4_meas'),
]
for label, col in rows:
    vals = [np.median(merged[merged['channel'].isin(chans)][col]) for chans in cs_map.values()]
    print(f'{label:<35} {vals[0]:>8.2f} {vals[1]:>8.2f} {vals[2]:>8.2f}')

print()
print('n per cell:', len(merged[merged['channel'].isin(cs_map['RGB'])]),
      '(3 channels x 4 groups, matched auto+man)')

# Save intermediate steps
merged[['channel','group_id',
        'measurement_std_auto','process_std_auto',
        'measurement_std_man','process_std_man',
        'r1_auto','r2_man','r3_proc','r4_meas']].sort_values(['channel','group_id']).to_csv(
    'output/uncertainty_measurement_workflow/noise_analysis/table2_verification_intermediate.csv',
    index=False, float_format='%.5f')
print()
print('Intermediate steps saved to analysis/table2_verification_intermediate.csv')
