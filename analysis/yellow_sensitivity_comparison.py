import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

datasets = {
    'More Yellow (Feb 13, no priming)': 'output/uncertainty_measurement_workflow/no_priming_20260213_073533_automated_darkest_more_yellow_7_1_1_group1_2_4',
    'Most Yellow (Feb 24, BEST)': 'output/uncertainty_measurement_workflow/BEST_20260224_123236_automated_darkest_most_yellow_7_1_1',
}

channels = ['LAB_B', 'RGB_G', 'LAB_A', 'B_prime', 'G_prime', 'A_prime']
display_names = ['LAB_B', 'RGB_G', 'LAB_A', "B'", "G'", "A'"]

print('R² for v_Y (Yellow Volume) - How well each channel differentiates yellow changes')
print('='*75)

results = {}
for ch, disp in zip(channels, display_names):
    results[disp] = []
    for ds_name, ds_path in datasets.items():
        try:
            df = pd.read_csv(f'{ds_path}/measurement_summary.csv')
            X = df[['v_Y']].values
            y = df[ch].values
            model = LinearRegression().fit(X, y)
            r2 = model.score(X, y)
            results[disp].append(r2)
        except Exception as e:
            results[disp].append(np.nan)
            print(f"Error loading {ds_path}: {e}")

print(f"{'Channel':<12} {'Low Yellow':<14} {'High Yellow':<14} {'Change':<10} {'Ratio'}")
print('-'*65)
for disp in display_names:
    low, high = results[disp]
    change = high - low
    ratio = high / low if low > 0.001 else float('inf')
    print(f'{disp:<12} {low:<14.3f} {high:<14.3f} {change:+.3f}      {ratio:.1f}x')
