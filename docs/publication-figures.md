# Publication Figures

This page provides interactive versions of the key BattMo publication figures.

## Figure 12

Cell balancing under equilibrium assumption. The interactive view shows the original balancing construction: graphite half-cell voltage, LNMO half-cell voltage, and full-cell voltage against areal capacity, with the low-rate experiment overlaid.

<div class="dual-plot-grid">
  <div id="figure12-discharge" class="plot-container"></div>
  <div id="figure12-ocv" class="plot-container"></div>
</div>

<p class="figure-note">Figure 12 uses the equilibrium balancing representation from the BattMo workflow: graphite and LNMO half-cell voltages are shown directly alongside the full-cell voltage and the low-rate experiment.</p>

## Figure 13

Initial and calibrated responses at `2C`, using the equilibrium-calibrated model and
the current six-parameter high-rate calibration.

<div id="figure13-plot" class="plot-container plot-large"></div>

<p class="figure-note">Compare the initial guess, calibrated response, and measured voltage.
The calibration adjusts the positive-electrode surface area, both solid diffusion
coefficients, and the three regional electrolyte Bruggeman coefficients.</p>

## Figure 14

Experimental voltages and P2D model results over different discharge rates.

<div id="figure14-plot" class="plot-container plot-large"></div>

<p class="figure-note">Figure 14 is the main BattMo-versus-experiment validation panel. The interactive version emphasizes the spread across rates while keeping the experiment and model traces distinguishable.</p>

## Figure 15

Initial relative sensitivities for all nine candidate parameters, before high-rate
calibration. The bars show `log10(abs(p*dJ/dp))` for the unnormalized voltage-error
objective `J` and physical parameter `p`. Larger values indicate a greater local
response to an equal fractional parameter change; the sign is omitted.

<div id="figure15-plot" class="plot-container plot-large"></div>

## Figure 16

Eigenvectors and eigenvalues of the BFGS Hessian at the calibrated solution, in
scaled parameter coordinates. Each column is an eigenmode; its eigenvalue measures
local objective curvature in that direction. The color scale shows signed
components from -1 to 1. Eigenvector signs are chosen so the largest component is positive.

<div id="figure16-plot" class="plot-container plot-large"></div>

## Generated figures

Open the original MATLAB figure exports below for the publication rendering.

<div id="publication-gallery" class="gallery-grid"></div>
