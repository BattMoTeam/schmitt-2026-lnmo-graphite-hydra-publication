# Graphite/LNMO BattMo Dataset and Workflow

This repository accompanies the paper "Comprehensive parameter and electrochemical dataset for a 1 Ah graphite/LNMO battery cell for physical modelling as a blueprint for data reporting in battery research" by Schmitt et al.

The repository demonstrates the P2D model calibration workflow described in the paper, starting with low-rate calibration under equilibrium assumptions, a calibration against high-rate data and final validation.

## Get Started

1. Clone this repository.
2. Clone BattMo locally.
3. Set `BATTMO_DIR` to the BattMo root containing `startupBattMo.m`.
4. Start MATLAB and run the `startupBattMo.m` script.


## Main Entry Points

- Low-rate calibration: `scripts/low-rate-calibration/runEquilibriumCalibration.m`
- High-rate calibration: `scripts/high-rate-calibration/runHighRateCalibration.m`
- Validation: `scripts/runValidation.m`
- Generate all figures in the paper: `scripts/exportPublicationFigures.m`
- Generate interactive documentation: `run-publication.ps1`


## FAIR Data and Interoperability

The data is available at https://doi.org/10.5281/zenodo.18256663 .

This repository includes FAIR-data exports alongside the primary BattMo workflow.

The BattMo JSON files are the canonical model inputs for the published workflow. The JSON-LD and BPX files are included to support machine readability and interoperability with PyBaMM and BattMo.

To export the BattMo validation reference curves from MATLAB, do
```matlab
startup
run(fullfile('scripts', 'exportValidationReference.m'));
```
Then compare BattMo and PyBaMM with
```powershell
python scripts/compare_battmo_pybamm.py
```
Some BattMo-specific features cannot be represented exactly in standard BPX:
- the graphite negative-electrode `j0(soc)` table
- independent volumetric surface area and active-material volume fraction
- cathode OCP boundary behavior outside the first tabulated stoichiometry point
Accordingly:
- the graphite `j0(soc)` data is approximated by a single BPX reaction-rate constant
- BattMo surface-area scaling is folded into exported reaction-rate constants
- the cathode OCP table includes a boundary extrapolation

See also
```powershell
run-publication.ps1 -IncludeBpx
```


## Documentation

To generate the interactive documentation, run from the repository root:

```powershell
.\run-publication.ps1
```
or
```powershell
python -m pip install -r requirements-docs.txt
python -m mkdocs serve
```

The repository includes a GitHub Actions workflow at `.github/workflows/github-pages.yml` that builds the MkDocs site on pushes to `main` and deploys the generated `site/` output to the `gh-pages` branch.

For GitHub Pages to publish that branch, set the repository Pages source to `Deploy from a branch`, branch `gh-pages`, folder `/ (root)`.


## Citation

Citation metadata is in [`CITATION.cff`](./CITATION.cff). The accompanying paper is available at `https://arxiv.org/abs/2601.10507`.

## License

This repository is distributed under the GNU General Public License v3.0 or later. See [`COPYING`](./COPYING).
