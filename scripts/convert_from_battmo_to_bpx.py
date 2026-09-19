from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np
from bpx import parse_bpx_obj
from scipy.io import loadmat

ROOT = Path(__file__).resolve().parents[1]
PARAMETERS_DIR = ROOT / "parameters"
VALIDATION_DATA = ROOT / "raw-data" / "TE_1473.mat"
DEFAULT_INPUT = PARAMETERS_DIR / "IMP5-70-120-H0B_graphite-lnmo_schmitt-2026_validation.battmo.json"
DEFAULT_OUTPUT = PARAMETERS_DIR / "IMP5-70-120-H0B_graphite-lnmo_schmitt-2026_validation.bpx.json"


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def parse_matlab_table(path: Path) -> np.ndarray:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"=\s*\[(.*?)\];", text, flags=re.DOTALL)
    if match is None:
        raise ValueError(f"Could not find MATLAB table in {path}")
    rows = []
    for line in match.group(1).splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append([float(item) for item in line.split()])
    table = np.array(rows, dtype=float)
    if (
        table.ndim != 2
        or table.shape[1] != 2
        or len(table) < 2
        or not np.isfinite(table).all()
        or not np.all(np.diff(table[:, 0]) > 0)
    ):
        raise ValueError(
            f"Expected a finite two-column table with increasing coordinates in {path}"
        )
    return table


def extend_table_to_unit_interval(table: np.ndarray) -> np.ndarray:
    x = table[:, 0]
    y = table[:, 1]
    rows = []
    if x[0] > 0.0:
        slope = (y[1] - y[0]) / (x[1] - x[0])
        rows.append([0.0, y[0] + slope * (0.0 - x[0])])
    rows.extend(table.tolist())
    if x[-1] < 1.0:
        slope = (y[-1] - y[-2]) / (x[-1] - x[-2])
        rows.append([1.0, y[-1] + slope * (1.0 - x[-1])])
    return np.array(rows, dtype=float)


def interpolate_table(table: np.ndarray, x_value: float) -> float:
    return float(np.interp(x_value, table[:, 0], table[:, 1]))


def electrolyte_diffusivity_nyman2008(concentration: np.ndarray) -> np.ndarray:
    scaled = concentration / 1000.0
    return 8.794e-11 * scaled**2 - 3.972e-10 * scaled + 4.862e-10


def electrolyte_conductivity_nyman2008(concentration: np.ndarray) -> np.ndarray:
    scaled = concentration / 1000.0
    return 0.1297 * scaled**3 - 2.51 * scaled**1.5 + 3.329 * scaled


def compute_active_fraction_within_solids(
    active_mass_fraction: float,
    active_density: float,
    binder_mass_fraction: float,
    binder_density: float,
    additive_mass_fraction: float,
    additive_density: float,
) -> float:
    active_specific_volume = active_mass_fraction / active_density
    binder_specific_volume = binder_mass_fraction / binder_density
    additive_specific_volume = additive_mass_fraction / additive_density
    solid_specific_volume = (
        active_specific_volume + binder_specific_volume + additive_specific_volume
    )
    return active_specific_volume / solid_specific_volume


def fit_bpx_reaction_rate_constant(
    j0_table: np.ndarray, theta_min: float, theta_max: float, surface_area_scale: float
) -> float:
    """Least-squares fit of j0 = F*K*sqrt(theta*(1-theta)) at nominal ce.

    BattMo's tabulated currents are A/cm2. The area ratio preserves the
    volumetric reaction strength while BPX uses spherical-particle geometry.
    """
    faraday = 96485.33212
    soc = j0_table[:, 0]
    j0 = j0_table[:, 1] * 1e4 * surface_area_scale
    sto = theta_min + soc * (theta_max - theta_min)
    mask = (sto > 0.0) & (sto < 1.0)
    if not np.any(mask):
        raise ValueError("No interior stoichiometry samples for kinetic fit")
    basis = faraday * np.sqrt(sto[mask] * (1.0 - sto[mask]))
    return float(np.dot(basis, j0[mask]) / np.dot(basis, basis))


def load_validation_data() -> dict:
    experiment = loadmat(VALIDATION_DATA, squeeze_me=True, struct_as_record=False)["experiment"]
    validation = {}
    for idx, (time_h, current, voltage) in enumerate(
        zip(experiment.time, experiment.current, experiment.voltage), start=1
    ):
        time_s = np.asarray(time_h, dtype=float) * 3600.0
        current_a = -np.asarray(current, dtype=float)
        voltage_v = np.asarray(voltage, dtype=float)
        validation[f"Discharge rate {idx}"] = {
            "Time [s]": time_s.tolist(),
            "Current [A]": current_a.tolist(),
            "Voltage [V]": voltage_v.tolist(),
        }
    return validation


def build_bpx_dict(
    input_path: Path = DEFAULT_INPUT,
    geometry_path: Path = PARAMETERS_DIR / "h0b-geometry-3d.json",
    *,
    functions_dir: Path | None = None,
    nominal_capacity: float = 1.0,
    upper_cutoff: float = 4.9,
) -> dict:
    """Convert the HYDRA single-active-material, isothermal parameter set to BPX 1.0."""
    params = load_json(input_path)
    geom_3d = load_json(geometry_path)
    functions_dir = functions_dir or input_path.parent
    if params.get("use_thermal", False):
        raise ValueError("Only isothermal BattMo inputs are supported")
    if nominal_capacity <= 0 or upper_cutoff <= params["Control"]["lowerCutoffVoltage"]:
        raise ValueError("Capacity must be positive and upper cutoff must exceed lower cutoff")
    for region, suffix in [("NegativeElectrode", "anode"), ("PositiveElectrode", "cathode")]:
        interface = params[region]["Coating"]["ActiveMaterial"]["Interface"]
        if interface["chargeTransferCoefficient"] != 0.5:
            raise ValueError("BPX conversion requires symmetric Butler-Volmer kinetics (alpha=0.5)")
        for field, name in [
            ("openCircuitPotential", f"computeOCP{suffix}H0b"),
            ("exchangeCurrentDensity", f"computeJ0{suffix}H0b"),
        ]:
            if interface[field].get("functionName") != name:
                raise ValueError(f"Unsupported {region} {field}: expected {name}")
    for field, name in [
        ("diffusionCoefficient", "computeDiffusionCoefficient_Nyman2008"),
        ("ionicConductivity", "computeElectrolyteConductivity_Nyman2008"),
    ]:
        if params["Electrolyte"][field].get("functionName") != name:
            raise ValueError(f"Unsupported electrolyte function: {field}")

    neg = params["NegativeElectrode"]["Coating"]
    pos = params["PositiveElectrode"]["Coating"]
    sep = params["Separator"]
    elyte = params["Electrolyte"]
    ctrl = params["Control"]
    geometry = geom_3d["Geometry"]

    neg_total_solid = neg["volumeFraction"]
    pos_total_solid = pos["volumeFraction"]
    neg_active_share = compute_active_fraction_within_solids(
        neg["ActiveMaterial"]["massFraction"],
        neg["ActiveMaterial"]["density"],
        neg["Binder"]["massFraction"],
        neg["Binder"]["density"],
        neg["ConductingAdditive"]["massFraction"],
        neg["ConductingAdditive"]["density"],
    )
    pos_active_share = compute_active_fraction_within_solids(
        pos["ActiveMaterial"]["massFraction"],
        pos["ActiveMaterial"]["density"],
        pos["Binder"]["massFraction"],
        pos["Binder"]["density"],
        pos["ConductingAdditive"]["massFraction"],
        pos["ConductingAdditive"]["density"],
    )
    neg_active = neg_total_solid * neg_active_share
    pos_active = pos_total_solid * pos_active_share
    neg_porosity = 1.0 - neg_total_solid
    pos_porosity = 1.0 - pos_total_solid

    region_bruggeman = (
        elyte["regionBruggemanCoefficients"]
        if elyte.get("useRegionBruggemanCoefficients", False)
        else dict.fromkeys(
            ["NegativeElectrode", "PositiveElectrode", "Separator"], elyte["bruggemanCoefficient"]
        )
    )
    neg_transport = neg_porosity ** region_bruggeman["NegativeElectrode"]
    pos_transport = pos_porosity ** region_bruggeman["PositiveElectrode"]
    sep_transport = sep["porosity"] ** region_bruggeman["Separator"]
    neg_conductivity = neg.get("effectiveElectronicConductivity")
    if neg_conductivity is None:
        neg_conductivity = (
            neg["electronicConductivity"] * neg_total_solid ** neg["bruggemanCoefficient"]
        )
    pos_conductivity = pos.get("effectiveElectronicConductivity")
    if pos_conductivity is None:
        pos_conductivity = (
            pos["electronicConductivity"] * pos_total_solid ** pos["bruggemanCoefficient"]
        )

    neg_ocp = extend_table_to_unit_interval(
        parse_matlab_table(functions_dir / "computeOCPanodeH0b.m")
    )
    pos_ocp = extend_table_to_unit_interval(
        parse_matlab_table(functions_dir / "computeOCPcathodeH0b.m")
    )
    neg_j0 = parse_matlab_table(functions_dir / "computeJ0anodeH0b.m")

    pos_j0 = parse_matlab_table(functions_dir / "computeJ0cathodeH0b.m")

    neg_radius = neg["ActiveMaterial"]["SolidDiffusion"]["particleRadius"]
    pos_radius = pos["ActiveMaterial"]["SolidDiffusion"]["particleRadius"]
    neg_surface_area_geom = 3.0 * neg_active / neg_radius
    pos_surface_area_geom = 3.0 * pos_active / pos_radius
    neg_surface_area_scale = (
        neg["ActiveMaterial"]["Interface"]["volumetricSurfaceArea"] / neg_surface_area_geom
    )
    pos_surface_area_scale = (
        pos["ActiveMaterial"]["Interface"]["volumetricSurfaceArea"] / pos_surface_area_geom
    )

    neg_theta_min = neg["ActiveMaterial"]["Interface"]["guestStoichiometry0"]
    neg_theta_max = neg["ActiveMaterial"]["Interface"]["guestStoichiometry100"]
    pos_theta_min = pos["ActiveMaterial"]["Interface"]["guestStoichiometry100"]
    pos_theta_max = pos["ActiveMaterial"]["Interface"]["guestStoichiometry0"]
    ocv_0 = interpolate_table(pos_ocp, pos_theta_max) - interpolate_table(neg_ocp, neg_theta_min)
    ocv_100 = interpolate_table(pos_ocp, pos_theta_min) - interpolate_table(neg_ocp, neg_theta_max)

    c_e0 = elyte["species"]["nominalConcentration"]
    neg_k_bpx = fit_bpx_reaction_rate_constant(
        neg_j0, neg_theta_min, neg_theta_max, neg_surface_area_scale
    )
    # Cathode SOC runs from maximum to minimum stoichiometry.
    pos_k_bpx = fit_bpx_reaction_rate_constant(
        pos_j0, pos_theta_max, pos_theta_min, pos_surface_area_scale
    )

    concentration_grid = np.linspace(0.0, 3000.0, 301)
    validation = load_validation_data()

    electrode_pair_area = geometry["width"] * geometry["length"]
    stack_thickness = geometry["nLayers"] * (
        params["NegativeElectrode"]["CurrentCollector"]["thickness"]
        + neg["thickness"]
        + sep["thickness"]
        + pos["thickness"]
        + params["PositiveElectrode"]["CurrentCollector"]["thickness"]
    )
    external_surface_area = 2.0 * (
        geometry["width"] * geometry["length"]
        + geometry["width"] * stack_thickness
        + geometry["length"] * stack_thickness
    )
    cell_volume = geometry["width"] * geometry["length"] * stack_thickness

    return {
        "Header": {
            "BPX": 1.0,
            "Title": "HYDRA graphite/LNMO validation parameter set",
            "Description": (
                "BPX export of the BattMo parameter set used in runValidation.m. "
                "Both electrodes: kinetics are approximated by a single BPX reaction-rate constant "
                "fitted to each BattMo j0(soc) table at nominal electrolyte concentration. "
                "Geometric surface areas preserve active volume; kinetic constants absorb area scaling. "
                "OCP tables are linearly extrapolated to stoichiometry endpoints. "
                "Geometry, nominal capacity and upper cutoff are supplementary inputs. "
                f"Source: {input_path.name}. Geometry: {geometry_path.name}."
            ),
            "References": "Schmitt et al., arXiv:2601.10507; BattMo parameter export",
            "Model": "DFN",
        },
        "Parameterisation": {
            "Cell": {
                "Electrode area [m2]": electrode_pair_area,
                "External surface area [m2]": external_surface_area,
                "Volume [m3]": cell_volume,
                "Number of electrode pairs connected in parallel to make a cell": geometry[
                    "nLayers"
                ],
                "Lower voltage cut-off [V]": ctrl["lowerCutoffVoltage"],
                "Upper voltage cut-off [V]": upper_cutoff,
                "Nominal cell capacity [A.h]": nominal_capacity,
                "Ambient temperature [K]": params["initT"],
                "Initial temperature [K]": params["initT"],
                "Reference temperature [K]": 298.15,
            },
            "Electrolyte": {
                "Initial concentration [mol.m-3]": c_e0,
                "Cation transference number": elyte["species"]["transferenceNumber"],
                "Diffusivity [m2.s-1]": {
                    "x": concentration_grid.tolist(),
                    "y": (
                        elyte.get("bgfactor", 1.0)
                        * electrolyte_diffusivity_nyman2008(concentration_grid)
                    ).tolist(),
                },
                "Conductivity [S.m-1]": {
                    "x": concentration_grid.tolist(),
                    "y": (
                        elyte.get("bgfactor", 1.0)
                        * electrolyte_conductivity_nyman2008(concentration_grid)
                    ).tolist(),
                },
            },
            "Negative electrode": {
                "Thickness [m]": neg["thickness"],
                "Porosity": neg_porosity,
                "Transport efficiency": neg_transport,
                "Conductivity [S.m-1]": neg_conductivity,
                "Minimum stoichiometry": neg_theta_min,
                "Maximum stoichiometry": neg_theta_max,
                "Maximum concentration [mol.m-3]": neg["ActiveMaterial"]["Interface"][
                    "saturationConcentration"
                ],
                "Particle radius [m]": neg_radius,
                "Surface area per unit volume [m-1]": neg_surface_area_geom,
                "Diffusivity [m2.s-1]": neg["ActiveMaterial"]["SolidDiffusion"][
                    "referenceDiffusionCoefficient"
                ],
                "Diffusivity activation energy [J.mol-1]": neg["ActiveMaterial"]["SolidDiffusion"][
                    "activationEnergyOfDiffusion"
                ],
                "OCP [V]": {"x": neg_ocp[:, 0].tolist(), "y": neg_ocp[:, 1].tolist()},
                "Entropic change coefficient [V.K-1]": 0.0,
                "Reaction rate constant [mol.m-2.s-1]": neg_k_bpx,
            },
            "Positive electrode": {
                "Thickness [m]": pos["thickness"],
                "Porosity": pos_porosity,
                "Transport efficiency": pos_transport,
                "Conductivity [S.m-1]": pos_conductivity,
                "Minimum stoichiometry": pos_theta_min,
                "Maximum stoichiometry": pos_theta_max,
                "Maximum concentration [mol.m-3]": pos["ActiveMaterial"]["Interface"][
                    "saturationConcentration"
                ],
                "Particle radius [m]": pos_radius,
                "Surface area per unit volume [m-1]": pos_surface_area_geom,
                "Diffusivity [m2.s-1]": pos["ActiveMaterial"]["SolidDiffusion"][
                    "referenceDiffusionCoefficient"
                ],
                "Diffusivity activation energy [J.mol-1]": pos["ActiveMaterial"]["SolidDiffusion"][
                    "activationEnergyOfDiffusion"
                ],
                "OCP [V]": {"x": pos_ocp[:, 0].tolist(), "y": pos_ocp[:, 1].tolist()},
                "Entropic change coefficient [V.K-1]": 0.0,
                "Reaction rate constant [mol.m-2.s-1]": pos_k_bpx,
                "Reaction rate constant activation energy [J.mol-1]": 0.0,
            },
            "Separator": {
                "Thickness [m]": sep["thickness"],
                "Porosity": sep["porosity"],
                "Transport efficiency": sep_transport,
            },
            "User-defined": {
                "Negative electrode total solid volume fraction": neg_total_solid,
                "Positive electrode total solid volume fraction": pos_total_solid,
                "Negative electrode active material share within solids": neg_active_share,
                "Positive electrode active material share within solids": pos_active_share,
                "Negative electrode active material volume fraction": neg_active,
                "Positive electrode active material volume fraction": pos_active,
                "Negative electrode inactive solid volume fraction": neg_total_solid - neg_active,
                "Positive electrode inactive solid volume fraction": pos_total_solid - pos_active,
                "Open-circuit voltage at 0% SOC [V]": ocv_0,
                "Open-circuit voltage at 100% SOC [V]": ocv_100,
                "BattMo negative electrode volumetric surface area [m-1]": neg["ActiveMaterial"][
                    "Interface"
                ]["volumetricSurfaceArea"],
                "BattMo positive electrode volumetric surface area [m-1]": pos["ActiveMaterial"][
                    "Interface"
                ]["volumetricSurfaceArea"],
                "BPX negative electrode surface area per unit volume [m-1]": neg_surface_area_geom,
                "BPX positive electrode surface area per unit volume [m-1]": pos_surface_area_geom,
                "BattMo negative electrode exchange-current density j0 [A.m-2]": {
                    "x": neg_j0[:, 0].tolist(),
                    "y": (neg_j0[:, 1] * 1e4).tolist(),
                },
                "BattMo positive electrode exchange-current density j0 [A.m-2]": {
                    "x": pos_j0[:, 0].tolist(),
                    "y": (pos_j0[:, 1] * 1e4).tolist(),
                },
                "BattMo negative electrode BPX-fitted reaction rate constant [mol.m-2.s-1]": neg_k_bpx,
            },
        },
        "Validation": validation,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert merged HYDRA BattMo parameters to BPX.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--geometry", type=Path, default=PARAMETERS_DIR / "h0b-geometry-3d.json")
    parser.add_argument(
        "--functions-dir", type=Path, help="MATLAB tables; defaults to input directory"
    )
    parser.add_argument(
        "--nominal-capacity", type=float, default=1.0, help="Nominal capacity [A.h]"
    )
    parser.add_argument("--upper-cutoff", type=float, default=4.9, help="Upper voltage cutoff [V]")
    args = parser.parse_args()
    protected = [args.input, args.geometry, VALIDATION_DATA]
    if args.output.resolve() in [path.resolve() for path in protected]:
        parser.error("Output must not overwrite an input file")
    try:
        converted = build_bpx_dict(
            args.input,
            args.geometry,
            functions_dir=args.functions_dir,
            nominal_capacity=args.nominal_capacity,
            upper_cutoff=args.upper_cutoff,
        )
        # Validate the complete document before creating or replacing the output.
        validated = parse_bpx_obj(converted).model_dump(by_alias=True, exclude_none=True)
        serialised = json.dumps(validated, indent=2, allow_nan=False) + "\n"
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialised, encoding="utf-8")
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"Conversion failed: {error}\n")
    print(f"Wrote schema-validated BPX: {args.output}")


if __name__ == "__main__":
    main()

"""
  Copyright 2021-2026 SINTEF Industry, Sustainable Energy Technology
  and SINTEF Digital, Mathematics & Cybernetics.

  This file is part of The Battery Modeling Toolbox BattMo

  BattMo is free software: you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  BattMo is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with BattMo.  If not, see <http://www.gnu.org/licenses/>.
"""
