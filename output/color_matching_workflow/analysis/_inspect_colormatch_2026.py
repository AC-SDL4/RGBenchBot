import pathlib, pandas as pd

base = pathlib.Path('output/color_matching_workflow')

runs_2026 = [f for f in sorted(base.iterdir())
             if f.is_dir() and f.name.startswith('2026') and 'virtual' not in f.name.lower()]

for folder in runs_2026:
    csv  = folder / 'color_matching_results.csv'
    if not csv.exists():
        print(folder.name, '-- NO CSV'); continue

    crops_dir = folder / 'center_crops'
    crops = list(crops_dir.glob('*.jp*g')) if crops_dir.exists() else []
    extra = [f.name for f in folder.iterdir()
             if f.name not in ('color_matching_results.csv', 'center_crops')
             and not f.name.startswith('.')]

    df = pd.read_csv(csv)
    n_data    = len(df[df['well'] != 'Target'])
    has_tgt   = 'Target' in df['well'].values
    meas_cols = [c for c in df.columns if c.startswith('measured_')]
    ch_names  = [c.replace('measured_', '') for c in meas_cols]

    valid_rows = df[df['well'] != 'Target'].copy()
    best_idx   = valid_rows['output'].idxmin()
    best       = valid_rows.loc[best_idx]

    print(folder.name)
    print(f'  wells={n_data}  has_target={has_tgt}  img_crops={len(crops)}  channels={ch_names}')
    if extra:
        print(f'  extra files: {extra}')

    if has_tgt:
        tgt = df[df['well'] == 'Target'].iloc[0]
        tvals = '  '.join(
            [f'{c.replace("measured_","")}={float(tgt[c]):.3f}'
             for c in meas_cols if not pd.isna(tgt[c])])
        print(f'  target measured: {tvals}')

    print(f'  best well: R={best["R_volume_ml"]:.2f} Y={best["Y_volume_ml"]:.2f}'
          f' B={best["B_volume_ml"]:.2f}  output={best["output"]:.5f}')

    # Flag weirdness
    flags = []
    if n_data < 20:
        flags.append(f'INCOMPLETE ({n_data} wells)')
    if not has_tgt:
        flags.append('NO TARGET ROW')
    if len(crops) == 0:
        flags.append('NO IMAGES')
    if n_data > 0 and len(crops) > 0 and len(crops) != n_data + (1 if has_tgt else 0):
        flags.append(f'CROP/WELL MISMATCH (crops={len(crops)} wells={n_data})')
    if flags:
        print(f'  *** FLAGS: {", ".join(flags)}')
    print()
