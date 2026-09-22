from __future__ import annotations

import json
import shutil
from pathlib import Path

from plotly.offline import get_plotlyjs

ROOT = Path(__file__).resolve().parents[1]
PUBLICATION_BPX_PATH = (
    ROOT / "parameters" / "IMP5-70-120-H0B_graphite-lnmo_schmitt-2026_validation.bpx.json"
)
PUBLICATION_BATTMO_PATH = (
    ROOT / "parameters" / "IMP5-70-120-H0B_graphite-lnmo_schmitt-2026_validation.battmo.json"
)
DOCS_DIR = ROOT / "docs"
DOCS_ASSETS_DIR = DOCS_DIR / "assets"
DATA_DIR = DOCS_ASSETS_DIR / "data"
IMAGES_DIR = DOCS_ASSETS_DIR / "images"
VENDOR_DIR = DOCS_ASSETS_DIR / "vendor"


def copy_file(source: Path, target: Path) -> str:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return str(target.relative_to(DOCS_DIR)).replace("\\", "/")


def write_plotly_bundle() -> str:
    target = VENDOR_DIR / "plotly.min.js"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(get_plotlyjs(), encoding="utf-8")
    return str(target.relative_to(DOCS_DIR)).replace("\\", "/")


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    VENDOR_DIR.mkdir(parents=True, exist_ok=True)

    plotly_bundle = write_plotly_bundle()
    validation_reference = load_json(ROOT / "figures" / "battmo-validation-reference.json")

    # The validation export now contains both voltage traces and spatial state fields.
    supporting_cases = []
    for case in validation_reference["cases"]:
        supporting_cases.append({
            key: value for key, value in case.items() if key not in ("experimental", "battmo")
        } | {
            "experimental_voltage_v": case["experimental"]["voltage_v"],
            "sim_voltage_v": case["battmo"]["voltage_v"],
            "exp_capacity_ah": case["experimental"]["capacity_ah"],
            "sim_capacity_ah": case["battmo"]["capacity_ah"],
            "time_h": [time_s / 3600 for time_s in case["battmo"]["time_s"]],
        })
    supporting_states_path = DATA_DIR / "battmo-validation-states.json"
    supporting_states_path.write_text(json.dumps({
        "title": "BattMo validation states for supporting interactive documentation",
        "cases": supporting_cases,
    }), encoding="utf-8")

    def prepare_data(source: Path, target_name: str, data_format: str = "json") -> dict[str, str]:
        return {"path": copy_file(source, DATA_DIR / target_name), "format": data_format}

    data_map = {
        "validation_reference": prepare_data(
            ROOT / "figures" / "battmo-validation-reference.json",
            "battmo-validation-reference.json",
        ),
        "figure12": prepare_data(
            ROOT / "figures" / "figure-12-cell-balancing-under-equilibrium-assumption.json",
            "figure-12-cell-balancing-under-equilibrium-assumption.json",
        ),
        "figure13": prepare_data(
            ROOT / "figures" / "figure-13-high-rate-calibration-at-2C.json",
            "figure-13-high-rate-calibration-at-2C.json",
        ),
        "figure14": prepare_data(
            ROOT / "figures" / "figure-14-experimental-voltages-and-p2d-results.json",
            "figure-14-experimental-voltages-and-p2d-results.json",
        ),
        "supporting_states": {
            "path": supporting_states_path.relative_to(DOCS_DIR).as_posix(),
            "format": "json",
        },
    }

    publication_gallery = [
        {
            "title": "Figure 12",
            "description": "Cell balancing under equilibrium assumption.",
            "image": copy_file(
                ROOT / "figures" / "figure-12-cell-balancing-under-equilibrium-assumption.png",
                IMAGES_DIR
                / "publication"
                / "figure-12-cell-balancing-under-equilibrium-assumption.png",
            ),
        },
        {
            "title": "Figure 13",
            "description": "Initial and calibrated responses at 2C using the current six-parameter calibration.",
            "image": copy_file(
                ROOT / "figures" / "figure-13-high-rate-calibration-at-2C.png",
                IMAGES_DIR / "publication" / "figure-13-high-rate-calibration-at-2C.png",
            ),
        },
        {
            "title": "Figure 14",
            "description": "Experimental voltages and P2D model results over different discharge rates.",
            "image": copy_file(
                ROOT / "figures" / "figure-14-experimental-voltages-and-p2d-results.png",
                IMAGES_DIR / "publication" / "figure-14-experimental-voltages-and-p2d-results.png",
            ),
        },
    ]

    for number, slug, description in (
        (15, "relative-parameter-sensitivities", "Initial relative sensitivities of the nine candidate parameters."),
        (16, "hessian-eigendecomposition", "Eigenvectors of the calibrated BFGS Hessian in scaled coordinates."),
    ):
        basename = f"figure-{number}-{slug}"
        data_map[f"figure{number}"] = prepare_data(
            ROOT / "figures" / f"{basename}.json", f"{basename}.json"
        )
        publication_gallery.insert(number - 12, {
            "title": f"Figure {number}",
            "description": description,
            "image": copy_file(
                ROOT / "figures" / f"{basename}.png",
                IMAGES_DIR / "publication" / f"{basename}.png",
            ),
        })

    supporting_gallery = []
    for index, case in enumerate(validation_reference["cases"], start=1):
        case_name = case["case_name"]
        supporting_gallery.append(
            {
                "title": f"{case_name} voltage curve",
                "description": "BattMo voltage curve against the experimental discharge trace.",
                "image": copy_file(
                    ROOT / "figures" / f"Case-{index}-voltage.png",
                    IMAGES_DIR / "supporting" / f"Case-{index}-voltage.png",
                ),
            }
        )
        supporting_gallery.append(
            {
                "title": f"{case_name} state dashboard",
                "description": "Electrolyte, potential, and particle-stoichiometry contour dashboard for the BattMo run.",
                "image": copy_file(
                    ROOT / "figures" / f"Case-{index}-state-dashboard.png",
                    IMAGES_DIR / "supporting" / f"Case-{index}-state-dashboard.png",
                ),
            }
        )

    fair_documents = [
        {
            "label": "BattMo validation JSON-LD",
            "description": "BattINFO/EMMO mappings of the merged validation parameters, with an embedded context and complete sourceData.",
            **prepare_data(
                ROOT / "linked-data" / (PUBLICATION_BATTMO_PATH.stem + ".jsonld"),
                PUBLICATION_BATTMO_PATH.stem + ".jsonld", "text",
            ),
        },
        {
            "label": "Merged BattMo validation parameters",
            "description": "Merged base, equilibrium, and high-rate BattMo parameters; geometry is supplied separately.",
            **prepare_data(
                PUBLICATION_BATTMO_PATH,
                PUBLICATION_BATTMO_PATH.name, "text",
            ),
        },
        {
            "label": "Publication BPX",
            "description": "BPX 1.0 parameters with all five measured discharge curves included under Validation.",
            **prepare_data(
                PUBLICATION_BPX_PATH,
                PUBLICATION_BPX_PATH.name, "text",
            ),
        },
        {
            "label": "BattMo base parameters",
            "description": "Canonical BattMo base parameter file used by the model workflow.",
            **prepare_data(ROOT / "parameters" / "h0b-base.json", "h0b-base.json", "text"),
        },
        {
            "label": "BattMo equilibrium calibration parameters",
            "description": "Low-rate calibrated BattMo parameters.",
            **prepare_data(
                ROOT / "parameters" / "equilibrium-calibration-parameters.json",
                "equilibrium-calibration-parameters.json", "text",
            ),
        },
        {
            "label": "BattMo high-rate calibration parameters",
            "description": "High-rate calibrated BattMo parameters used in validation.",
            **prepare_data(
                ROOT / "parameters" / "high-rate-calibration-parameters.json",
                "high-rate-calibration-parameters.json", "text",
            ),
        },
        {
            "label": "Software citation metadata",
            "description": "Machine-readable citation metadata for the repository.",
            **prepare_data(ROOT / "CITATION.cff", "CITATION.cff", "text"),
        },
    ]

    manifest = {
        "summary": {
            "validation_cases": len(validation_reference["cases"]),
            "publication_figures": 5,
            "supporting_dashboards": len(supporting_gallery),
            "fair_documents": len(fair_documents),
        },
        "vendor": {"plotly_bundle": plotly_bundle},
        "data": data_map,
        "publication_gallery": publication_gallery,
        "supporting_gallery": supporting_gallery,
        "fair_documents": fair_documents,
    }

    manifest_json = DATA_DIR / "site-manifest.json"
    manifest_json.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote {manifest_json}")


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
