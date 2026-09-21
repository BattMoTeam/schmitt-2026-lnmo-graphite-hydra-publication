# Graphite/LNMO BattMo Dataset and Workflow

This repository accompanies the paper "Comprehensive parameter and
electrochemical dataset for a 1 Ah graphite/LNMO battery cell for
physical modelling as a blueprint for data reporting in battery
research" by Schmitt et al.

The repository demonstrates the P2D model calibration workflow
described in the paper, starting with low-rate calibration under
equilibrium assumptions, a calibration against high-rate data and
final validation.

## Get Started

See [Dependencies](#dependencies) for the software needed by each
workflow.

Clone this repository with its submodules (the configured URLs use
GitHub SSH access):

```sh
git clone --recurse-submodules git@github.com:BattMoTeam/schmitt-2026-lnmo-graphite-hydra-publication.git
cd schmitt-2026-lnmo-graphite-hydra-publication
```

Start MATLAB in this repository and run `startup` to configure the
project and BattMo.

## Dependencies

The MATLAB calibration, Python interoperability, and documentation
workflows have separate dependencies so you can install the software
needed for the stages you intend to run.

| Dependency | Why it is needed |
| --- | --- |
| Git with GitHub SSH access | Clones this repository and the submodules using their configured URLs. |
| MATLAB | Runs calibration, BattMo validation, sensitivity analysis, and publication figure generation. |
| BattMo and its submodules, including MRST | Provide the battery models, grids, automatic differentiation, and numerical solvers. BattMo is pinned to a specific revision; `git clone --recurse-submodules` initializes it and its dependencies. |
| Python | Runs JSON-LD/BPX conversion and the Python comparison and plotting scripts. The interoperability workflow has been checked with Python 3.12. |

For an existing clone, initialize the pinned submodules with:

```sh
git submodule update --init --recursive
```

Startup finds the local `BattMo/` submodule automatically. Set
`BATTMO_DIR` only if you want to use a separate BattMo checkout; it
must point to the root containing `startupBattMo.m`.

Install the packages for BPX conversion and Python validation from
`requirements.txt`:

```sh
python -m pip install -r requirements.txt
```

| Package | Why it is needed |
| --- | --- |
| `pybamm[bpx]` | Imports the BPX parameter set and runs the DFN simulations for comparison with BattMo. |
| `bpx==0.5.0` | Validates exports against the BPX 1.0 layout used here; the `bpx` 1.1 series uses a different document layout. |
| `numpy` | Handles numerical arrays, interpolation, kinetic fitting, and voltage-error calculations. |
| `scipy` | Reads the experimental MATLAB data in `raw-data/TE_1473.mat` for inclusion in BPX. |
| `matplotlib` | Plots BattMo, experimental, and PyBaMM voltage curves. |

The JSON-LD converter uses only the Python standard library and works
offline; it does not require these packages or a separate BattINFO
checkout.

Building the documentation site additionally uses
`requirements-docs.txt`: `mkdocs` builds the site, and `plotly`
supplies the JavaScript bundle for interactive figures. These packages
are not needed to run calibration or BPX conversion.

```sh
python -m pip install -r requirements-docs.txt
```


## Entry Points

The main entry point is `runReproduction`, which runs `startup` and
the calibration, validation, and sensitivity scripts to generate
Figures 12–16:

```matlab
runReproduction
```

To run individual stages, first run `startup`, then use the following
scripts:

| Script | Publication figures | Purpose |
| --- | --- | --- |
| `scripts/low-rate-calibration/runEquilibriumCalibration.m` | Figure 12 | Equilibrium calibration and cell-balancing plots |
| `scripts/high-rate-calibration/runHighRateCalibration.m` | Figures 13 and 16 | Six-parameter high-rate calibration and Hessian analysis |
| `scripts/runValidation.m` | Figure 14 | Validation over the five experimental discharge rates |
| `scripts/high-rate-calibration/plotSensitivities.m` | Figure 15 | Initial sensitivities for all nine candidate parameters; Figure 15 is the relative-sensitivity plot |

Figures save beside their scripts. High-rate calibration also saves
figures and Hessian results in a run-specific subfolder beside
`runHighRateCalibration.m`. The individual stages read the existing
calibration JSON files where needed; `runReproduction` regenerates
them in sequence.

`runValidation` also saves `figures/battmo-validation-reference.json`
from the same simulation states for the Python comparisons. This
export is included in `runReproduction`.

The main sensitivity-reporting function is
`scripts/high-rate-calibration/computeSensitivities.m`.  It takes a
calibration object, an objective function, and the objective scaling,
and reports scaled, physical, and relative parameter sensitivities.

After calibration, run `createOptJson` (`scripts/createOptJson.m`) to
export the merged calibrated parameters to
`parameters/IMP5-70-120-H0B_graphite-lnmo_schmitt-2026_validation.battmo.json`.
This is a separate step from `runReproduction`.

Typical durations are `1 - 2 h` for full reproduction, `1 min`
for equilibrium calibration, `1 - 2 hrs` for high-rate calibration,
and `1 - 2 min` for validation.

For Python validation, run `python run-validation.py` after
`runValidation` or `runReproduction` (typical duration: `5 - 15
min`). It plots BattMo against the measurements, exports BPX, and runs
the PyBaMM comparison using the same Python interpreter.

These are rough wall-clock estimates on a typical workstation or
laptop. The high-rate calibration dominates runtime and can vary
substantially with MATLAB release, CPU, and BattMo setup.

## FAIR Data and Interoperability

The data is available at https://doi.org/10.5281/zenodo.18256663 .

This repository includes FAIR-data exports alongside the primary
BattMo workflow.

The BattMo JSON files are the canonical model inputs for the published
workflow. In particular,
`parameters/IMP5-70-120-H0B_graphite-lnmo_schmitt-2026_validation.battmo.json`
is the single-file merged BattMo counterpart to the publication BPX
export. The JSON-LD and BPX files are included to support machine
readability and interoperability with PyBaMM and BattMo.

The four main BattMo parameter files in `parameters/` are:

- `h0b-base.json`: base material and cell parameters.
- `equilibrium-calibration-parameters.json`: calibrated low-rate parameters.
- `high-rate-calibration-parameters.json`: calibrated high-rate parameters.
- `IMP5-70-120-H0B_graphite-lnmo_schmitt-2026_validation.battmo.json`: the merged calibrated parameters.

The recursive merge applies base, equilibrium, then high-rate
parameters, with later values taking precedence, matching
`runValidation.m` through `runHydra.m`. Current collectors and
regional electrolyte Bruggeman coefficients are enabled. Geometry
files remain separate; `runHydra.m` adds the validation geometry and
scales collector conductivities during model setup.

Convert the merged BattMo parameter file to JSON-LD with:

```sh
python scripts/convert_from_battmo_to_jsonld.py
```

This standalone script reads only
`parameters/IMP5-70-120-H0B_graphite-lnmo_schmitt-2026_validation.battmo.json`
and writes
`linked-data/IMP5-70-120-H0B_graphite-lnmo_schmitt-2026_validation.battmo.jsonld`.
The output uses BattINFO/EMMO component and quantity mappings, with an
embedded context. Model-specific settings use a separate project
namespace; the complete source JSON, including function definitions,
is retained in `sourceData`.  All parameter values come from the
merged input file; the converter does not reread or merge the base and
calibration files.

Convert the merged calibrated BattMo parameters to BPX with:

```sh
python scripts/convert_from_battmo_to_bpx.py
```

This writes
`parameters/IMP5-70-120-H0B_graphite-lnmo_schmitt-2026_validation.bpx.json`
and validates it against the [BPX 1.0
schema](https://github.com/FaradayInstitution/BPX) before writing. The
converter reads numerical model parameters from the merged
`IMP5-70-120-H0B_graphite-lnmo_schmitt-2026_validation.battmo.json`,
without re-merging calibration files. It also reads
`h0b-geometry-3d.json` for pouch geometry and the four referenced OCP
and exchange-current MATLAB tables in the input directory. It supports
these HYDRA functions and the Nyman electrolyte functions, rather than
arbitrary MATLAB code.

The supplementary publication defaults, absent from the merged JSON,
are 1 A.h nominal capacity and 4.9 V upper cutoff.  Conversion is
isothermal, with reference temperature 298.15 K. External area and
volume are estimated from the rectangular electrode stack, excluding
tabs and packaging.  The export always includes all five discharge
curves from `raw-data/TE_1473.mat` under `Validation`, with time in
seconds, discharge current in amperes, and voltage in volts.  The
converter performs schema validation; the comparison script below runs
PyBaMM.

The BattMo validation reference curves are exported by
`runValidation`, including when called through `runReproduction`. If
you have not run validation yet, run it in MATLAB:

```matlab
startup
runValidation
```
Then compare BattMo and PyBaMM with
```sh
python scripts/compare_battmo_pybamm.py
```

The PyBaMM run uses an isothermal DFN model starting at 100% SOC, with
constant current until the experimental end time or the BPX lower
voltage cutoff. It does not reproduce BattMo's constant-voltage
continuation. RMSE uses trapezoidal integration of squared voltage
error over the shared time interval, without extrapolation; the
summary reports this interval and the PyBaMM termination
reason. Signed voltage differences are PyBaMM minus BattMo.

Some BattMo-specific features cannot be represented exactly in
standard BPX:
- both electrodes’ `j0(soc)` tables
- independent volumetric surface area and active-material volume
  fraction
- cathode OCP boundary behavior outside the first tabulated
  stoichiometry point

Accordingly:
- each `j0(soc)` table is approximated by a least-squares BPX
  reaction-rate constant at nominal electrolyte concentration; BPX
  adds concentration dependence absent from these BattMo tables
- BattMo surface-area scaling is folded into exported reaction-rate
  constants
- the cathode OCP table includes a boundary extrapolation

Regional electrolyte Bruggeman coefficients are preserved through each
region's BPX `Transport efficiency`, calculated as
`porosity^BruggemanCoefficient`. The PyBaMM BPX importer recovers the
corresponding coefficients from transport efficiency and porosity.
Electrode electronic Bruggeman corrections are already included in the
exported effective conductivities, so PyBaMM does not apply them
again.

See also
```sh
python run-validation.py
```
## Interactive Documentation

After updating the calibration parameters, run `runValidation` and
`exportPublicationFigures` in MATLAB. The latter refreshes the
interactive data for Figures 12–14 and the supporting state dashboards
using the saved calibration parameters; it does not rerun the
optimizations.

Then refresh the Python summaries, FAIR exports, and site assets:

```sh
python run-validation.py
python scripts/convert_from_battmo_to_jsonld.py
python scripts/prepare_docs_site.py
python -m mkdocs build --strict
```

Run `createOptJson` before the Python exports if the merged BattMo
file has not yet been updated. Documentation dependencies are listed
in [Dependencies](#dependencies).  The generated site is in `site/`;
`python -m mkdocs serve` provides a local preview.

## Citation

Citation metadata is in [`CITATION.cff`](./CITATION.cff). The
accompanying paper is available at `https://arxiv.org/abs/2601.10507`.

## License

This repository is distributed under the GNU General Public License
v3.0 or later. See [`COPYING`](./COPYING).
