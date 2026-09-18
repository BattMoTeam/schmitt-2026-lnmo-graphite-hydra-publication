"""Run Python-side validation after exporting the MATLAB reference curves."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--include-bpx", action="store_true", help="Also run BPX / PyBaMM interoperability checks."
    )
    parser.add_argument("--python-exe", help="Python executable used to run the workflow scripts.")
    args = parser.parse_args()

    reference = ROOT / "figures" / "battmo-validation-reference.json"
    if not reference.is_file():
        parser.exit(1, f"Missing {reference}. Run runReproduction in MATLAB first.\n")

    venv_python = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    python = args.python_exe or (
        str(venv_python) if venv_python.is_file() else os.environ.get("PYTHON_EXE") or sys.executable
    )
    print(f"Repository root: {ROOT}", flush=True)
    print(f"Python: {python}", flush=True)
    print("Running optional Python-side validation workflow...", flush=True)

    try:
        subprocess.run([python, "scripts/plot_battmo_validation.py"], cwd=ROOT, check=True)
        if args.include_bpx:
            print("Running optional BPX / PyBaMM FAIR interoperability workflow...", flush=True)
            verification_output = ROOT / "codex" / "figures" / "bpx_verification_summary.json"
            verification_output.parent.mkdir(parents=True, exist_ok=True)
            commands = [
                ["scripts/export_battmo_parameters.py"],
                ["scripts/export_bpx.py"],
                ["scripts/verify_bpx.py", "--output", str(verification_output)],
                ["scripts/compare_battmo_pybamm.py"],
            ]
            for command in commands:
                subprocess.run([python, *command], cwd=ROOT, check=True)
    except subprocess.CalledProcessError as error:
        print(f"Command failed (exit {error.returncode}): {error.cmd}", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"Validation failed: {error}", file=sys.stderr)
        return 1

    prefix = "IMP5-70-120-H0B_graphite-lnmo_schmitt-2026"
    print("\nValidation outputs:")
    print(f"  figures/publication/{prefix}_battmo-vs-experiment-summary.json")
    print(f"  figures/publication/{prefix}_battmo-vs-experiment.png")
    if args.include_bpx:
        print("\nOptional BPX / PyBaMM outputs:")
        print(f"  parameters/{prefix}_validation.battmo.json")
        print(f"  parameters/{prefix}_validation.bpx.json")
        print("  codex/figures/bpx_verification_summary.json")
        print("  codex/figures/battmo-vs-pybamm-bpx-summary.json")
        print("  codex/figures/battmo-vs-pybamm-bpx.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
