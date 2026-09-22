"""Convert a merged BattMo parameter file to self-contained BattINFO/EMMO JSON-LD.

Uses only the Python standard library. The embedded context is a subset of
https://w3id.org/emmo/domain/battery/context, retrieved on 2026-09-18.
Project-specific model settings use the explicitly separate battmo namespace.
The complete source JSON is retained as a JSON-LD 1.1 JSON literal:
https://www.w3.org/TR/json-ld11/#json-literals
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
from typing import Any
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "parameters" / (
    "IMP5-70-120-H0B_graphite-lnmo_schmitt-2026_validation.battmo.json"
)
PROJECT_IRI = "https://github.com/BattMoTeam/schmitt-2026-lnmo-graphite-hydra-publication"

# Embedded ontology mappings make the converter and its output independent of
# network access and of a separate BattINFO checkout or context file.
ONTOLOGY_CONTEXT = {
    "emmo": "https://w3id.org/emmo#",
    "electrochemistry": "https://w3id.org/emmo/domain/electrochemistry#",
    "battery": "https://w3id.org/emmo/domain/battery#",
    "ActivationEnergy": "electrochemistry:electrochemistry_d7f8cab9_b035_4ecd_be63_292672572526",
    "ActiveMaterial": "electrochemistry:electrochemistry_79d1b273_58cd_4be6_a250_434817f7c261",
    "AmountConcentration": "emmo:EMMO_d5be1faf_0c56_4f5a_9b78_581e6dee949f",
    "AmperePerSquareMetre": "emmo:AmperePerSquareMetre",
    "BatteryCell": "battery:battery_68ed592a_7924_45d0_a108_94d6275d57f0",
    "Binder": "electrochemistry:electrochemistry_68eb5e35_5bd8_47b1_9b7f_f67224fa291e",
    "BruggemanCoefficient": "electrochemistry:electrochemistry_5c34b3b5_c9c4_477d_809a_3f682f995aa9",
    "ChargeTransferCoefficient": "electrochemistry:electrochemistry_a4dfa5c1_55a9_4285_b71d_90cf6613ca31",
    "ConductiveAdditive": "electrochemistry:electrochemistry_82fef384_8eec_4765_b707_5397054df594",
    "CurrentCollector": "electrochemistry:electrochemistry_212af058_3bbb_419f_a9c6_90ba9ebb3706",
    "Density": "emmo:EMMO_06448f64_8db6_4304_8b2c_e785dba82044",
    "Diffusivity": "electrochemistry:electrochemistry_37b24a94_cae0_4d7a_9519_9f7692dec607",
    "Electrode": "electrochemistry:electrochemistry_0f007072_a8dd_4798_b865_1bf9363be627",
    "ElectrodeCoating": "electrochemistry:electrochemistry_403c300e_09b9_400b_943b_04e82a3cfb56",
    "Electrolyte": "electrochemistry:electrochemistry_fb0d9eef_92af_4628_8814_e065ca255d59",
    "ElectronicConductivity": "electrochemistry:electrochemistry_ce74d2dc_d496_4116_b2fb_3e83d88bc744",
    "ExchangeCurrentDensity": "electrochemistry:electrochemistry_e9fd9ef9_adfe_46cb_b2f9_4558468a25e7",
    "IonTransportNumber": "emmo:EMMO_d97b27cb_61a4_4568_a38b_4edd4f224acc",
    "IonicConductivity": "electrochemistry:electrochemistry_25dabdc2_68bf_4a38_8cbe_11be017358bc",
    "JoulePerKilogramKelvin": "emmo:JoulePerKilogramKelvin",
    "JoulePerMole": "emmo:JoulePerMole",
    "Kelvin": "emmo:Kelvin",
    "KilogramPerCubicMetre": "emmo:KilogramPerCubicMetre",
    "LowerVoltageLimit": "electrochemistry:electrochemistry_534dd59c_904c_45d9_8550_ae9d2eb6bbc9",
    "MassFraction": "emmo:EMMO_7c055d65_2929_40e1_af4f_4bf10995ad50",
    "MaximumConcentration": "electrochemistry:electrochemistry_47287d09_6108_45ca_ac65_8b9451b1065e",
    "Metre": "emmo:Metre",
    "MolePerCubicMetre": "emmo:MolePerCubicMetre",
    "NumberOfElectronsTransferred": "electrochemistry:electrochemistry_abfadc99_6e43_4d37_9b04_7fc5b0f327ae",
    "OpenCircuitVoltage": "electrochemistry:electrochemistry_9c657fdc_b9d3_4964_907c_f9a6e8c5f52b",
    "ParticleRadius": "electrochemistry:electrochemistry_b92e382f_5109_4f60_ab5e_c89d340419a9",
    "Porosity": "emmo:EMMO_3a6578ac_aee0_43b9_9bc6_1eb208c8c9a9",
    "RealData": "emmo:EMMO_18d180e4_5e3e_42f7_820c_e08951223486",
    "Separator": "electrochemistry:electrochemistry_331e6cca_f260_4bf8_af55_35304fe1bbe0",
    "SiemensPerMetre": "emmo:SiemensPerMetre",
    "SpecificHeatCapacity": "emmo:EMMO_b4f4ed28_d24c_4a00_9583_62ab839abeca",
    "SquareMetrePerSecond": "emmo:SquareMetrePerSecond",
    "StateOfCharge": "electrochemistry:electrochemistry_8b2aaa50_bbe1_45da_8778_8898326246a2",
    "StoichiometricCoefficientAtSOC0": "electrochemistry:electrochemistry_f22bd1ec_faca_4335_92a5_a1687154c622",
    "StoichiometricCoefficientAtSOC100": "electrochemistry:electrochemistry_38ab058e_3912_48c2_a7eb_76d25d000820",
    "ThermalConductivity": "emmo:EMMO_8dd40ec6_2c5a_43f3_bf64_cadcd447a1c1",
    "ThermodynamicTemperature": "emmo:EMMO_affe07e4_e9bc_4852_86c6_69e26182a17f",
    "Thickness": "emmo:EMMO_43003c86_9d15_433b_9789_ee2940920656",
    "UnitOne": "emmo:EMMO_5ebd5e01_0ed3_49a2_a30d_cd05cbe72978",
    "Volt": "emmo:Volt",
    "VolumeFraction": "emmo:EMMO_a8eb87b5_4d10_4137_a75c_e04ee59ca095",
    "VolumetricSurfaceArea": "electrochemistry:electrochemistry_a5571263_f153_448f_84a3_cd18092cf8fa",
    "WattPerMetreKelvin": "emmo:WattPerMetreKelvin",
    "hasActiveMaterial": {
        "@id": "electrochemistry:electrochemistry_860aa941_5ff9_4452_8a16_7856fad07bee",
        "@type": "@id"
    },
    "hasBinder": {
        "@id": "electrochemistry:electrochemistry_056a5fab_3d99_46bd_8eb1_6e89a368e1a7",
        "@type": "@id"
    },
    "hasCoating": {
        "@id": "electrochemistry:electrochemistry_4df9926d_d4f2_4955_93f3_a03c5edc5383",
        "@type": "@id"
    },
    "hasConductiveAdditive": {
        "@id": "electrochemistry:electrochemistry_c830c469_60c3_4380_8382_4df13a32a1e7",
        "@type": "@id"
    },
    "hasCurrentCollector": {
        "@id": "electrochemistry:electrochemistry_cc8c2c5d_cf3d_444d_a7e8_44ec4c06a88e",
        "@type": "@id"
    },
    "hasElectrolyte": {
        "@id": "electrochemistry:electrochemistry_3bd08946_4e81_455d_9fca_dc7a5ead9315",
        "@type": "@id"
    },
    "hasMeasurementUnit": {
        "@id": "emmo:EMMO_bed1d005_b04e_4a90_94cf_02bc678a8569",
        "@type": "@vocab"
    },
    "hasNegativeElectrode": {
        "@id": "electrochemistry:electrochemistry_5d299271_3f68_494f_ab96_3db9acdd3138",
        "@type": "@id"
    },
    "hasNumericalPart": {
        "@id": "emmo:EMMO_8ef3cd6d_ae58_4a8d_9fc0_ad8f49015cd0",
        "@type": "@id"
    },
    "hasNumericalValue": "emmo:EMMO_faf79f53_749d_40b2_807c_d34244c192f4",
    "hasPositiveElectrode": {
        "@id": "electrochemistry:electrochemistry_8e9cf965_9f92_46e8_b678_b50410ce3616",
        "@type": "@id"
    },
    "hasProperty": {
        "@id": "emmo:EMMO_e1097637_70d2_4895_973f_2396f04fa204",
        "@type": "@id"
    },
    "hasSeparator": {
        "@id": "electrochemistry:electrochemistry_9317be62_e602_4343_a72d_02c87201b9f6",
        "@type": "@id"
    }
}

COMPONENTS = {
    "PositiveElectrode": ("hasPositiveElectrode", "Electrode"),
    "NegativeElectrode": ("hasNegativeElectrode", "Electrode"),
    "Electrolyte": ("hasElectrolyte", "Electrolyte"),
    "Separator": ("hasSeparator", "Separator"),
    "Coating": ("hasCoating", "ElectrodeCoating"),
    "ActiveMaterial": ("hasActiveMaterial", "ActiveMaterial"),
    "Binder": ("hasBinder", "Binder"),
    "ConductingAdditive": ("hasConductiveAdditive", "ConductiveAdditive"),
    "CurrentCollector": ("hasCurrentCollector", "CurrentCollector"),
}

# BattMo values are in SI units. Fractions and stoichiometries stay dimensionless;
# function definitions retain their complete argument lists and representations.
PROPERTIES = {
    "initT": ("ThermodynamicTemperature", "Kelvin"),
    "SOC": ("StateOfCharge", "UnitOne"),
    "density": ("Density", "KilogramPerCubicMetre"),
    "thickness": ("Thickness", "Metre"),
    "volumeFraction": ("VolumeFraction", "UnitOne"),
    "massFraction": ("MassFraction", "UnitOne"),
    "porosity": ("Porosity", "UnitOne"),
    "electronicConductivity": ("ElectronicConductivity", "SiemensPerMetre"),
    "effectiveElectronicConductivity": ("ElectronicConductivity", "SiemensPerMetre"),
    "ionicConductivity": ("IonicConductivity", "SiemensPerMetre"),
    "diffusionCoefficient": ("Diffusivity", "SquareMetrePerSecond"),
    "referenceDiffusionCoefficient": ("Diffusivity", "SquareMetrePerSecond"),
    "particleRadius": ("ParticleRadius", "Metre"),
    "saturationConcentration": ("MaximumConcentration", "MolePerCubicMetre"),
    "nominalConcentration": ("AmountConcentration", "MolePerCubicMetre"),
    "guestStoichiometry0": ("StoichiometricCoefficientAtSOC0", "UnitOne"),
    "guestStoichiometry100": ("StoichiometricCoefficientAtSOC100", "UnitOne"),
    "volumetricSurfaceArea": ("VolumetricSurfaceArea", "qudt:PER-M"),
    "bruggemanCoefficient": ("BruggemanCoefficient", "UnitOne"),
    "chargeTransferCoefficient": ("ChargeTransferCoefficient", "UnitOne"),
    "activationEnergyOfDiffusion": ("ActivationEnergy", "JoulePerMole"),
    "activationEnergyOfReaction": ("ActivationEnergy", "JoulePerMole"),
    "numberOfElectronsTransferred": ("NumberOfElectronsTransferred", "UnitOne"),
    "transferenceNumber": ("IonTransportNumber", "UnitOne"),
    "lowerCutoffVoltage": ("LowerVoltageLimit", "Volt"),
    "thermalConductivity": ("ThermalConductivity", "WattPerMetreKelvin"),
    "specificHeatCapacity": ("SpecificHeatCapacity", "JoulePerKilogramKelvin"),
    "openCircuitPotential": ("OpenCircuitVoltage", "Volt"),
    "exchangeCurrentDensity": ("ExchangeCurrentDensity", "AmperePerSquareMetre"),
}


def json_pointer(path: tuple[str, ...]) -> str:
    """Identify a source field without ambiguity for keys containing '/' or '~'."""
    return "".join("/" + key.replace("~", "~0").replace("/", "~1") for key in path)


def validate_json(value: Any) -> None:
    """Reject values that cannot be represented faithfully in standard JSON."""
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise ValueError("JSON object keys must be strings")
            validate_json(child)
    elif isinstance(value, list):
        for child in value:
            validate_json(child)
    elif isinstance(value, float) and not math.isfinite(value):
        raise ValueError("JSON numbers must be finite")
    elif value is not None and not isinstance(value, (str, int, float, bool)):
        raise ValueError(f"Unsupported JSON value: {type(value).__name__}")


def build_jsonld(parameters: dict[str, Any], source_name: str) -> dict[str, Any]:
    """Describe the input without merging, recalibrating, or deriving new parameters."""
    if not isinstance(parameters, dict) or not parameters:
        raise ValueError("The BattMo input must be a nonempty JSON object")
    validate_json(parameters)
    canonical = json.dumps(parameters, sort_keys=True, separators=(",", ":"), allow_nan=False)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    dataset_id = f"urn:sha256:{digest}"
    context = {
        "@version": 1.1,
        "schema": "https://schema.org/",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "qudt": "http://qudt.org/vocab/unit/",
        "battmo": PROJECT_IRI + "/vocab/battmo#",
        **deepcopy(ONTOLOGY_CONTEXT),
        "sourceData": {"@id": "battmo:sourceData", "@type": "@json"},
        "sourceValue": {"@id": "battmo:sourceValue", "@type": "@json"},
    }

    def node_id(path: tuple[str, ...]) -> str:
        return dataset_id + "#" + quote(json_pointer(path), safe="/~")

    def property_node(key: str, value: Any, path: tuple[str, ...]) -> dict[str, Any]:
        mapping = PROPERTIES.get(key)
        if len(path) > 1 and path[-2] == "regionBruggemanCoefficients":
            mapping = ("BruggemanCoefficient", "UnitOne")
        node = {
            "@id": node_id(path),
            "@type": "battmo:ModelParameter",
            "rdfs:label": key,
            "battmo:sourcePath": json_pointer(path),
            "sourceValue": deepcopy(value),
        }
        if mapping is not None:
            quantity_type, unit = mapping
            node["@type"] = [quantity_type, "battmo:ModelParameter"]
            node["hasMeasurementUnit"] = unit
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                node["hasNumericalPart"] = {
                    "@type": "RealData",
                    "hasNumericalValue": value,
                }
        return node

    def component_node(data: dict[str, Any], path: tuple[str, ...], kind: str) -> dict:
        node = {"@id": node_id(path), "@type": kind}
        if path:
            node["rdfs:label"] = path[-1]
            node["battmo:sourcePath"] = json_pointer(path)
        properties = []
        model_blocks = []
        for key, value in data.items():
            child_path = (*path, key)
            if isinstance(value, dict) and key in COMPONENTS:
                relation, child_kind = COMPONENTS[key]
                node[relation] = component_node(value, child_path, child_kind)
            elif isinstance(value, dict) and key in ("Interface", "SolidDiffusion"):
                # BattMo groups these properties by equation block; BattINFO attaches
                # them to the active material. Source paths keep the distinction explicit.
                properties.extend(
                    property_node(name, child, (*child_path, name))
                    for name, child in value.items()
                )
            elif isinstance(value, dict) and key not in PROPERTIES:
                model_blocks.append(component_node(value, child_path, "battmo:ModelBlock"))
            else:
                properties.append(property_node(key, value, child_path))
        if properties:
            node["hasProperty"] = properties
        if model_blocks:
            node["battmo:hasModelBlock"] = model_blocks
        return node

    return {
        "@context": context,
        **component_node(parameters, (), "BatteryCell"),
        "@id": dataset_id,
        "schema:name": source_name,
        "schema:description": "Calibrated BattMo parameters with BattINFO/EMMO quantity mappings.",
        "schema:encodingFormat": "application/ld+json",
        "battmo:sourceFilename": source_name,
        "battmo:canonicalSourceSha256": digest,
        "sourceData": deepcopy(parameters),
    }


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Reject duplicate keys instead of silently discarding parameter values."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Merged BattMo JSON file")
    parser.add_argument(
        "--output", type=Path, help="Output path (default: linked-data/<input filename>.jsonld)"
    )
    args = parser.parse_args()
    output = args.output or ROOT / "linked-data" / args.input.with_suffix(".jsonld").name
    if args.input.resolve() == output.resolve():
        parser.error("Input and output paths must differ")
    try:
        parameters = json.loads(args.input.read_text(encoding="utf-8"), object_pairs_hook=unique_object)
        document = build_jsonld(parameters, args.input.name)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(document, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    except (OSError, ValueError) as error:
        parser.exit(1, f"Conversion failed: {error}\n")
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
