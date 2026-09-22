"""Compare constant-current BPX DFN discharges with exported BattMo validation curves."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pybamm

ROOT = Path(__file__).resolve().parents[1]
PUBLICATION_BPX_PATH = (
    ROOT
    / "parameters"
    / ("IMP5-70-120-H0B_graphite-lnmo_schmitt-2026_validation.bpx.json")
)
FIGURES_DIR = ROOT / "figures"


def compute_metrics(
    reference_time, reference_voltage, comparison_time, comparison_voltage
) -> dict:
    """Compute voltage errors over the shared time interval.

    RMSE uses trapezoidal integration of squared error. Signed errors are comparison
    minus reference. Neither curve is extrapolated.
    """
    reference_time, reference_voltage, comparison_time, comparison_voltage = (
        np.asarray(values, dtype=float)
        for values in (
            reference_time,
            reference_voltage,
            comparison_time,
            comparison_voltage,
        )
    )
    start = max(reference_time[0], comparison_time[0])
    end = min(reference_time[-1], comparison_time[-1])
    if end <= start:
        raise ValueError("BattMo and PyBaMM curves have no positive-duration overlap")
    time_interp = np.unique(
        np.concatenate(([start, end], reference_time, comparison_time))
    )
    time_interp = time_interp[(time_interp >= start) & (time_interp <= end)]
    error = np.interp(time_interp, comparison_time, comparison_voltage) - np.interp(
        time_interp, reference_time, reference_voltage
    )
    duration = end - start
    rmse_v = float(np.sqrt(np.trapezoid(error**2, time_interp) / duration))
    return {
        "common_start_s": float(start),
        "common_end_s": float(end),
        "common_duration_s": float(duration),
        "battmo_overlap_fraction": float(
            duration / (reference_time[-1] - reference_time[0])
        ),
        "rmse_v": rmse_v,
        "max_abs_v": float(np.max(np.abs(error))),
        "initial_voltage_diff_v": float(error[0]),
        "final_voltage_diff_v": float(error[-1]),
    }


def run_pybamm_case(
    parameter_values: pybamm.ParameterValues,
    current_a: float,
    duration_s: float,
    *,
    output_period_s: float = 10.0,
    rtol: float = 1e-6,
    atol: float = 1e-6,
    mesh_points: int = 20,
) -> dict:
    """Run from 100% SOC until the requested time or the model's voltage cutoff."""
    parameters = parameter_values.copy()
    parameters.update({"Current function [A]": current_a})
    model = pybamm.lithium_ion.DFN({"thermal": "isothermal"})
    solver = pybamm.CasadiSolver(mode="safe", rtol=rtol, atol=atol)
    var_pts = dict.fromkeys(["x_n", "x_s", "x_p", "r_n", "r_p"], mesh_points)
    simulation = pybamm.Simulation(
        model, parameter_values=parameters, solver=solver, var_pts=var_pts
    )
    time_grid = np.linspace(
        0, duration_s, max(2, int(np.ceil(duration_s / output_period_s)) + 1)
    )
    solution = simulation.solve(t_eval=time_grid)
    if solution.termination not in ("final time", "event: Minimum voltage [V]"):
        raise ValueError(f"Unexpected PyBaMM termination: {solution.termination}")
    return {
        "time_s": solution["Time [s]"].entries.tolist(),
        "voltage_v": solution["Voltage [V]"].entries.tolist(),
        "termination": solution.termination,
    }


def make_plot(cases: list[dict], output_path: Path) -> None:
    rows = (len(cases) + 1) // 2
    fig, axes = plt.subplots(
        rows, 2, figsize=(11, 3.8 * rows), constrained_layout=True, squeeze=False
    )
    for ax, case in zip(axes.flat, cases):
        for key, label, color, style in (
            ("experimental", "Experiment", "black", "--"),
            ("battmo", "BattMo", "#1f77b4", "-"),
            ("pybamm", "PyBaMM BPX", "#d62728", "-"),
        ):
            curve = case[key]
            capacity = np.asarray(curve["time_s"]) * case["current_a"] / 3600
            ax.plot(
                capacity, curve["voltage_v"], color=color, linestyle=style, label=label
            )
        ax.set_title(f"{case['case_name']} ({case['current_a']:.3g} A)")
        ax.set_xlabel("Capacity / Ah")
        ax.set_ylabel("Voltage / V")
        ax.grid(True, alpha=0.25)
        ax.legend(loc="best")
    for ax in list(axes.flat)[len(cases) :]:
        ax.set_visible(False)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def compare(
    reference_json: Path, bpx_path: Path, summary_path: Path, figure_path: Path
) -> list[dict]:
    """Run the exported discharge cases and save a plot and compact metrics summary."""
    reference_json, bpx_path, summary_path, figure_path = (
        Path(path).resolve()
        for path in (reference_json, bpx_path, summary_path, figure_path)
    )
    if summary_path in (reference_json, bpx_path) or figure_path in (
        reference_json,
        bpx_path,
        summary_path,
    ):
        raise ValueError(
            "Output paths must be distinct and must not overwrite input files"
        )
    reference = json.loads(reference_json.read_text(encoding="utf-8"))
    parameter_values = pybamm.ParameterValues.create_from_bpx(bpx_path, target_soc=1.0)
    cases_out = []
    for case in reference["cases"]:
        result = run_pybamm_case(
            parameter_values,
            float(case["current_a"]),
            float(case["experimental"]["time_s"][-1]),
        )
        metrics = compute_metrics(
            case["battmo"]["time_s"],
            case["battmo"]["voltage_v"],
            result["time_s"],
            result["voltage_v"],
        )
        cases_out.append({**case, "metrics": metrics, "pybamm": result})

    summary = {
        "reference_file": str(reference_json),
        "bpx_file": str(bpx_path),
        "summary_metrics": [
            {
                "case_name": case["case_name"],
                "current_a": case["current_a"],
                "pybamm_termination": case["pybamm"]["termination"],
                **case["metrics"],
            }
            for case in cases_out
        ],
    }
    serialised = json.dumps(summary, indent=2, allow_nan=False) + "\n"
    make_plot(cases_out, figure_path)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(serialised, encoding="utf-8")
    return summary["summary_metrics"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reference",
        type=Path,
        default=FIGURES_DIR / "battmo-validation-reference.json",
    )
    parser.add_argument("--bpx", type=Path, default=PUBLICATION_BPX_PATH)
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=FIGURES_DIR / "battmo-vs-pybamm-bpx-summary.json",
    )
    parser.add_argument(
        "--figure-output",
        type=Path,
        default=FIGURES_DIR / "battmo-vs-pybamm-bpx.png",
    )
    args = parser.parse_args()
    metrics = compare(args.reference, args.bpx, args.summary_output, args.figure_output)
    print(json.dumps(metrics, indent=2, allow_nan=False))
    print(f"Wrote {args.summary_output}")
    print(f"Wrote {args.figure_output}")


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
