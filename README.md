# Graphite/LNMO BattMo Dataset and Workflow

This repository accompanies the paper "Comprehensive parameter and electrochemical dataset for a 1 Ah graphite/LNMO battery cell for physical modelling as a blueprint for data reporting in battery research" by Schmitt et al.

The repository demonstrates the P2D model calibration workflow described in the paper, starting with low-rate calibration under equilibrium assumptions, a calibration against high-rate data and final validation.

## Get Started

1. Clone this repository.
2. Clone BattMo locally.
3. Set `BATTMO_DIR` to the BattMo root containing `startupBattMo.m`.
4. Start MATLAB in this repository and run `startup.m` to configure the project and BattMo.


## Entry Points

After running `startup.m`, use these main calibration and validation scripts:

- Low-rate calibration only (typical duration: `2 - 10 min`): `scripts/low-rate-calibration/runEquilibriumCalibration.m`
- High-rate calibration only (typical duration: `45 - 180 min`): `scripts/high-rate-calibration/runHighRateCalibration.m`
- Validation plot only (typical duration: `5 - 15 min`): `scripts/runValidation.m`

The main sensitivity-reporting function is `scripts/high-rate-calibration/computeSensitivities.m`.
It takes a calibration object, an objective function, and the objective scaling, and reports
scaled, physical, and relative parameter sensitivities.

Additional workflows:

- Full MATLAB-side publication reproduction (typical duration: `1 - 3 h`): `runReproduction`
- Figure export only (typical duration: `10 - 30 min`): `scripts/exportPublicationFigures.m`
- Python-side validation summary only (typical duration: `< 1 min`; `5 - 15 min` with `--include-bpx`): `python run-validation.py`

These are rough wall-clock estimates on a typical workstation or laptop. The high-rate calibration dominates runtime and can vary substantially with MATLAB release, CPU, and BattMo setup.

## FAIR Data and Interoperability

The data is available at https://doi.org/10.5281/zenodo.18256663 .

This repository includes FAIR-data exports alongside the primary BattMo workflow.

The BattMo JSON files are the canonical model inputs for the published workflow. In particular, `parameters/IMP5-70-120-H0B_graphite-lnmo_schmitt-2026_validation.battmo.json` is the single-file merged BattMo counterpart to the publication BPX export. The JSON-LD and BPX files are included to support machine readability and interoperability with PyBaMM and BattMo.

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
```sh
python run-validation.py --include-bpx
```
## Citation

Citation metadata is in [`CITATION.cff`](./CITATION.cff). The accompanying paper is available at `https://arxiv.org/abs/2601.10507`.

## License

This repository is distributed under the GNU General Public License v3.0 or later. See [`COPYING`](./COPYING).
