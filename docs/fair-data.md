# FAIR Data

The publication-facing repository includes both the primary BattMo parameter files and interoperable FAIR-data exports.

- `JSON-LD` maps the merged validation parameters to BattINFO/EMMO terms. Its embedded
  context supports offline use, and `sourceData` preserves the complete BattMo input.
- `BPX` provides the BPX 1.0 parameter set and all five measured discharge curves.
- The BattMo JSON files remain the canonical model input for the published workflow.

The merged file combines base, equilibrium, and high-rate parameters; geometry remains
separate. The JSON-LD and BPX exports both read this merged file.

BPX kinetics approximate the measured exchange-current tables, with surface-area scaling
included in the fitted reaction-rate constants. Regional electrolyte Bruggeman coefficients
are represented by `Transport efficiency = porosity^BruggemanCoefficient`. Electrode
conductivities already include their electronic Bruggeman corrections.

<div class="control-row">
  <label for="fair-data-select">Document</label>
  <select id="fair-data-select">
    <option>Loading...</option>
  </select>
</div>

<div id="fair-data-meta" class="callout"></div>

<pre id="fair-data-viewer" class="json-viewer">Loading document...</pre>
