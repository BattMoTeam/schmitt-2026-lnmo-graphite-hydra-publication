# Graphite/LNMO BattMo Dataset and Workflow

This repository accompanies the paper "Comprehensive parameter and electrochemical dataset for a 1 Ah graphite/LNMO battery cell for physical modelling as a blueprint for data reporting in battery research" by Schmitt et al.

The repository demonstrates the P2D model calibration workflow described in the paper, starting with low-rate calibration under equilibrium assumptions, a calibration against high-rate data and final validation.

## Get Started

1. Clone this repository.
2. Clone BattMo locally.
3. Set `BATTMO_DIR` to the BattMo root containing `startupBattMo.m`.
4. Start MATLAB in this repository and run `startup.m` to configure the project and BattMo.


## Entry Points

The main entry point is `runReproduction`, which runs `startup` and the calibration,
validation, and sensitivity scripts to generate Figures 12–16:

```matlab
runReproduction
```

To run individual stages, first run `startup`, then use the following scripts:

| Script | Publication figures | Purpose |
| --- | --- | --- |
| `scripts/low-rate-calibration/runEquilibriumCalibration.m` | Figure 12 | Equilibrium calibration and cell-balancing plots |
| `scripts/high-rate-calibration/runHighRateCalibration.m` | Figures 13 and 16 | Six-parameter high-rate calibration and Hessian analysis |
| `scripts/runValidation.m` | Figure 14 | Validation over the five experimental discharge rates |
| `scripts/high-rate-calibration/plotSensitivities.m` | Figure 15 | Initial sensitivities for all nine candidate parameters; Figure 15 is the relative-sensitivity plot |

Figures save beside their scripts. High-rate calibration also saves figures and Hessian
results in a run-specific subfolder beside `runHighRateCalibration.m`. The individual stages
read the existing calibration JSON files where needed; `runReproduction` regenerates them
in sequence.

The main sensitivity-reporting function is `scripts/high-rate-calibration/computeSensitivities.m`.
It takes a calibration object, an objective function, and the objective scaling, and reports
scaled, physical, and relative parameter sensitivities.

After calibration, run `createOptJson` (`scripts/createOptJson.m`) to export the merged
calibrated parameters to
`parameters/IMP5-70-120-H0B_graphite-lnmo_schmitt-2026_validation.battmo.json`.
This is a separate step from `runReproduction`.

Typical durations are `1 - 3 h` for full reproduction, `2 - 10 min` for equilibrium
calibration, `45 - 180 min` for high-rate calibration, and `5 - 15 min` for validation.

For a Python-side validation summary, run `python run-validation.py` after exporting the
validation reference curves as described below (typical duration: `< 1 min`;
`5 - 15 min` with `--include-bpx`).

These are rough wall-clock estimates on a typical workstation or laptop. The high-rate calibration dominates runtime and can vary substantially with MATLAB release, CPU, and BattMo setup.

## FAIR Data and Interoperability

The data is available at https://doi.org/10.5281/zenodo.18256663 .

This repository includes FAIR-data exports alongside the primary BattMo workflow.

The BattMo JSON files are the canonical model inputs for the published workflow. In particular, `parameters/IMP5-70-120-H0B_graphite-lnmo_schmitt-2026_validation.battmo.json` is the single-file merged BattMo counterpart to the publication BPX export. The JSON-LD and BPX files are included to support machine readability and interoperability with PyBaMM and BattMo.

The four main BattMo parameter files in `parameters/` are:

- `h0b-base.json`: base material and cell parameters.
- `equilibrium-calibration-parameters.json`: calibrated low-rate parameters.
- `high-rate-calibration-parameters.json`: calibrated high-rate parameters.
- `IMP5-70-120-H0B_graphite-lnmo_schmitt-2026_validation.battmo.json`: the merged calibrated parameters.

The recursive merge applies base, equilibrium, then high-rate parameters, with later values
taking precedence, matching `runValidation.m` through `runHydra.m`. Current collectors and
regional electrolyte Bruggeman coefficients are enabled. Geometry files remain separate;
`runHydra.m` adds the validation geometry and scales collector conductivities during model setup.

Convert the merged BattMo parameter file to JSON-LD with:

```sh
python scripts/convert_from_battmo_to_jsonld.py
```

This standalone script reads only
`parameters/IMP5-70-120-H0B_graphite-lnmo_schmitt-2026_validation.battmo.json` and writes
`linked-data/IMP5-70-120-H0B_graphite-lnmo_schmitt-2026_validation.battmo.jsonld`.
Use `--input` and `--output` to override these paths. Conversion requires only the Python
standard library and works offline. The output uses BattINFO/EMMO component and quantity
mappings, with an embedded context. Model-specific settings use a separate project namespace;
the complete source JSON, including function definitions, is retained in `sourceData`.
All parameter values come from the merged input file; the converter does not reread or merge
the base and calibration files. It replaces the former `generate_optimization_linked_data.py`
workflow and requires no separate BattINFO checkout.

PyLD is listed in `requirements.txt` for validation, not for running the converter.
Run the four regression tests, including offline JSON-LD expansion and RDF conversion, with:

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -p test_battmo_jsonld.py
```

Convert the merged calibrated BattMo parameters to BPX with:

```sh
python scripts/convert_from_battmo_to_bpx.py
```

This writes `parameters/IMP5-70-120-H0B_graphite-lnmo_schmitt-2026_validation.bpx.json`
and validates it against the [BPX 1.0 schema](https://github.com/FaradayInstitution/BPX)
before writing. The converter reads numerical model parameters from the merged
`IMP5-70-120-H0B_graphite-lnmo_schmitt-2026_validation.battmo.json`, without re-merging
calibration files. It also reads `h0b-geometry-3d.json` for pouch geometry and the four
referenced OCP and exchange-current MATLAB tables in the input directory. It supports
these HYDRA functions and the Nyman electrolyte functions, rather than arbitrary MATLAB code.

Use `--input`, `--output`, `--geometry`, and `--functions-dir` to override those paths.
The supplementary publication defaults, absent from the merged JSON, are 1 A.h nominal
capacity and 4.9 V upper cutoff; override them with `--nominal-capacity` and `--upper-cutoff`.
Conversion is isothermal, with reference temperature 298.15 K. External area and volume
are estimated from the rectangular electrode stack, excluding tabs and packaging.
Measurements are optional: `--validation-data raw-data/TE_1473.mat` embeds discharge curves.
The converter performs schema validation; the comparison script below runs PyBaMM.
Dependencies are in `requirements.txt`; `bpx==0.5.0` implements the BPX 1.0 layout used here.

```sh
python -m unittest discover -s tests -p test_battmo_bpx.py
```

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
- both electrodes’ `j0(soc)` tables
- independent volumetric surface area and active-material volume fraction
- cathode OCP boundary behavior outside the first tabulated stoichiometry point
Accordingly:
- each `j0(soc)` table is approximated by a least-squares BPX reaction-rate constant at nominal electrolyte concentration; BPX adds concentration dependence absent from these BattMo tables
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
