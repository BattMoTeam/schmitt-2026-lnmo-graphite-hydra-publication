from __future__ import annotations

import argparse
import json
from pathlib import Path

from publication_names import PUBLICATION_BATTMO_PATH


ROOT = Path(__file__).resolve().parents[1]
PARAMETERS_DIR = ROOT / "parameters"


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def merge_dicts(base: dict, update: dict) -> dict:
    merged = dict(base)
    for key, value in update.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


def build_battmo_parameter_dict() -> dict:
    merged_battmo = load_json(PARAMETERS_DIR / "h0b-opt.json")
    geometry = load_json(PARAMETERS_DIR / "h0b-geometry-3d.json")

    params = merge_dicts(merged_battmo, geometry)
    return params


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export the final merged BattMo parameter set used for validation."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PUBLICATION_BATTMO_PATH,
        help="Output BattMo parameter file path",
    )
    args = parser.parse_args()

    merged = build_battmo_parameter_dict()
    args.output.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    print(f"Wrote {args.output}")


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
