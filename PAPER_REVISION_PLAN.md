# Paper Revision Plan
**Date:** 2026-08-10

---

## Narrative structure (keep this order exactly)

1. **Build** — We made this dispenser.
2. **Calibrate** — We measured its actual flow rate and volume accuracy.
3. **Characterize uncertainty** — We separated camera noise from dispenser noise.
4. **Color channel S/N** — We ranked color channels by their signal-to-noise ratio (Limit of Detection).
5. **Which colorspace?** — We extended that to complete 3-channel sets.
6. **Color matching** — We ran the optimizer and evaluated how close it got to the target recipe.

Each step motivates the next. No step should be cut.

---

## Section-by-section plan

### § 0.1 — Dispenser calibration — KEEP AS-IS
Nothing wrong here. The linear time–mass fit ($m = 0.3786\ \mathrm{mL/s}$, $R^2 = 0.9948$),
the CV table justifying $V_{\min} = 0.025\ \mathrm{mL}$, the priming protocol, and the
post-conditioning volume validation are all solid.

Minor optional improvements (not urgent):
- Test the intercept $b$ for significance (it's ~1 mg, probably just noise).
- Expand validation to $n > 2$ per target to avoid zero-σ artefacts like the 0.15 mL row.

---

### § 0.2 — Uncertainty — REWORK

#### Keep
- The nested uncertainty framework: $U^{\text{meas}}$ (repeat images of same well) vs
  $U^{\text{proc}}$ (repeat wells at same recipe).  The math (eq. 6–9) is correct.
- The finding: process uncertainty dominates measurement by ~18×. This is the key
  result of this section. **State it in one sentence and move on.**
- The decision not to pool different composition regimes — this is correct and should
  be stated explicitly.
- The note that normalized channels are not automatically lower-variance (they change
  form, not noise level).
- One-sentence acknowledgement of the rep-1 outlier: *"The first of 6 replicates per
  well showed elevated noise from camera auto-exposure settling; all 6 replicates are
  used throughout since the production workflow does not discard it, and channel
  rankings are unchanged when rep 1 is excluded."*

#### Replace
- **Range-normalized $\sigma = U/\Delta_c$** as a cross-channel comparison metric.
  The theoretical range $\Delta_c$ is not realized in practice and is not the same
  fraction of practical range for different channels. Comparisons like
  "averaged across all channels = 1.97×10⁻³" obscure which channels are actually good.
  **Replace with LoD (mL) throughout.**

- **Standardized regression coefficients** ($\beta_R$, $\beta_Y$, derived $\gamma_B$)
  as the primary sensitivity measure. These are unitless, so they cannot be combined
  with σ to give LoD. The $\gamma_B = -(\beta_R + \beta_Y)$ construction is correct
  but needs to be explained as a consequence of the fixed-volume constraint, not
  presented as an independently fitted third coefficient.
  **Replace with raw regression coefficients** (channel units per mL of dye). These
  give sensitivity in the correct scale to compute LoD.

- **Response norm $\|\gamma\|_2$** as a channel ranking. Because $\gamma_B$ is
  algebraically determined by $\gamma_R$ and $\gamma_Y$, this norm is redundant.
  **Remove.** The LoD bar chart replaces it.

- **Stability–sensitivity scatter plot (Fig 7).** The two axes have incompatible
  units. "Distance to the preferred corner" is undefined.
  **Replace with the LoD ranking bar chart** (0–0.05 mL scale, all three dyes
  side by side on the same axis).

#### Add (new analysis, done 2026-08-10)
- **Multivariate channel-set LoD.** For a 3-channel set with sensitivity matrix $S$
  and noise covariance $\Sigma$:
  $$\mathrm{Cov}(\hat{v}) = (S^\top \Sigma^{-1} S)^{-1}$$
  The diagonal gives the per-dye LoD when using the full set jointly.
  Key result: **LAB (L\*, a\*, b\*) gives the best worst-dye LoD (~0.0025 mL) and
  is nearly immune to the rep-1 noise source** (−7.8% improvement when rep 1
  excluded, vs −58.8% for raw RGB).

  Include a brief explanation of why all sets are near-singular: $v_R + v_Y + v_B =
  0.9\ \mathrm{mL}$ is constant by design, so the three dye volumes are collinear
  as regressors. The optimizer only needs to estimate ratios, not independent
  absolute volumes — the pseudo-inverse handles this correctly.

#### Figures for § 0.2 (revised)
| # | What | Replaces |
|---|---|---|
| A | Measurement vs process uncertainty bar chart (one bar per dataset) | Fig 3 — keep |
| B | Per-channel LoD ranking bar chart (shared 0–0.05 mL y-axis) | Fig 6 (response norm) + Fig 7 (scatter) |
| C | Channel-set multivariate LoD bar chart (LAB, RGB, HSV, normalized, Best3) | New |

Table 2 (mean normalized uncertainties) can stay as a supporting table but should
not be the primary comparison. Add a column for LoD.

---

### § 0.3 — Color matching — REWORK EVALUATION METRIC

#### Keep
- The overall framing: uncertainty/sensitivity analysis guided the choice of
  colorspace for the optimizer. This is the payoff of §0.2.
- The visual comparison of target crop vs best-match well (Fig 9). The RGBN visual
  result is genuinely good and should be shown.
- Running multiple colorspaces (RGBN, LABN, Sobol) as ablation.

#### The core problem: output-space vs input-space evaluation

The current paper compares runs by their **objective value** at the best well — i.e.,
color distance in the *optimizer's own objective space* (RGBN distance, LABN distance,
etc.). This is wrong for two reasons:

1. **Different objective spaces are not comparable.** RGBN distance 0.013 and LABN
   distance 0.064 are numbers from two different functions. You cannot declare a
   winner from these.

2. **Output space doesn't answer the right question.** We want to know if the
   optimizer found the *correct recipe*, not whether the measured color happens to
   be close to the target color under a particular metric. A run that minimizes RGBN
   distance may incidentally produce the right recipe, or may find a completely
   different recipe that looks similar under RGBN but is far from correct.

#### The correct evaluation: input space (composition distance)

For each run, take the best well found by the optimizer and compute the Euclidean
distance in **dye volume space** between the dispensed recipe and the true target
recipe:

$$d_{\text{input}} = \sqrt{(V_R - V_R^*)^2 + (V_Y - V_Y^*)^2 + (V_B - V_B^*)^2} \quad [\mathrm{mL}]$$

This is interpretable (mL away from the correct recipe), comparable across all
runs (same metric regardless of colorspace used by the optimizer), and directly
answers the practical question: *"Did the optimizer find the right formulation?"*

**Prerequisites:** The ground-truth target composition $(V_R^*, V_Y^*, V_B^*)$ must
be known for all runs. If the target was an image of a known dye mixture, this
is available. If the target was an arbitrary image, this approach requires knowing
what composition produced it.

#### Revised § 0.3 structure

1. State that evaluation is in composition space ($d_{\text{input}}$ in mL).
2. Table: for each physical run, report best $d_{\text{input}}$ achieved, at which well.
3. Best-so-far $d_{\text{input}}$ convergence plot (one curve per method, all on the
   same axis in mL).
4. Visual comparison (Fig 9 style) retained as a qualitative check.
5. Conclusion: which colorspace found the best recipe, and by how much.

The conclusion may change. If RGBN still wins in composition space, the paper's
claim holds. If LAB wins, or they tie, the paper must be updated — but it will then
be internally consistent with the §0.2 finding that LAB has the best LoD.

---

## Summary of changes

| Section | Action | Reason |
|---|---|---|
| § 0.1 Calibration | **Keep** | Correct and well-executed |
| § 0.2 Uncertainty decomposition | **Keep** framework | Correct methodology |
| § 0.2 Range-normalized σ as cross-channel metric | **Replace with LoD** | Theoretical range ≠ practical range; unfair comparison |
| § 0.2 Standardized sensitivity regression | **Replace with raw coefficients** | Standardized β's cannot be used to compute LoD |
| § 0.2 Response norm \|γ\|₂ + scatter plot | **Remove / replace** | Units incompatible; LoD bar chart is cleaner and more informative |
| § 0.2 Channel-set analysis | **Add** | Missing; directly answers "which colorspace?" |
| § 0.3 Objective-value comparison | **Replace with composition-space distance** | Comparing different objective functions is invalid; input space is the right question |

---

## Completed analysis (available in codebase)

Scripts in `tests/analysis/`:
- `combined_best_mar13_lod.py` — per-channel LoD (σ/sensitivity) for 18 channels,
  48 wells, both rep-1 conditions. Outputs: `lod_summary.csv`, `lod_heatmap.png`,
  `lod_ranking.png`.
- `channel_set_lod.py` — multivariate set LoD for LAB, RGB, HSV, normalized variants,
  Best3. Outputs: `channel_set_lod.csv`, `channel_set_lod.png`.

Still needed:
- Script to evaluate color-matching runs in composition space ($d_{\text{input}}$).
  Requires: per-well dispensed recipe and known target composition for each run.
