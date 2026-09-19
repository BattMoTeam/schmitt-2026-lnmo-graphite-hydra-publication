"""Plot BattMo validation results, export BPX, and compare with PyBaMM."""

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent


def main() -> None:
    reference = ROOT / "figures" / "battmo-validation-reference.json"
    if not reference.is_file():
        raise FileNotFoundError(
            f"Missing {reference}. Run runValidation or runReproduction in MATLAB first."
        )

    for script in (
        "plot_battmo_validation.py",
        "convert_from_battmo_to_bpx.py",
        "compare_battmo_pybamm.py",
    ):
        print(f"Running {script}...", flush=True)
        subprocess.run([sys.executable, str(ROOT / "scripts" / script)], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
