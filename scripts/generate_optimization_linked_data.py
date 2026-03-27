from __future__ import annotations

import json
import os
import subprocess
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from publication_names import PUBLICATION_PREFIX


ROOT = SCRIPT_DIR.parents[0]
LINKED_DATA_DIR = ROOT / "linked-data"
OUTPUT_JSON_PATH = LINKED_DATA_DIR / f"{PUBLICATION_PREFIX}_optimization.json"
OUTPUT_JSONLD_PATH = LINKED_DATA_DIR / f"{PUBLICATION_PREFIX}_optimization.jsonld"

BATTINFO_ENV_VARS = ("BATTINFO_DIR", "BATTINFO_ROOT", "BATTINFO_REPO")
DEFAULT_BATTINFO_ROOT = ROOT.parents[1] / "battery-genome" / "BattINFO"

CONVERTER_PROPERTY_TYPES = {
    "concentration": "AmountConcentration",
    "density": "Density",
    "mass_fraction": "MassFraction",
    "porosity": "Porosity",
    "thickness": "Thickness",
    "volume_fraction": "VolumeFraction",
}

CONVERTER_COATING_PROPERTY_TYPES = {
    **CONVERTER_PROPERTY_TYPES,
    "thickness": "CalenderedCoatingThickness",
}

UNIT_IRIS = {
    "1": "emmo:UnitOne",
    "J/mol": "emmo:JoulePerMole",
    "K": "emmo:Kelvin",
    "S/m": "emmo:SiemensPerMetre",
    "V": "emmo:Volt",
    "m": "emmo:Metre",
    "m^2/s": "emmo:SquareMetrePerSecond",
    "mol/m^3": "emmo:MolePerCubicMetre",
    "1/m": "emmo:ReciprocalMetre",
}

GENERIC_PROPERTY_TYPES = {
    "activation_energy_of_lithium_diffusivity": ["ActivationEnergy"],
    "activation_energy_of_reaction": ["ActivationEnergy"],
    "charge_transfer_coefficient": ["ChargeTransferCoefficient"],
    "concentration": ["AmountConcentration"],
    "density": ["Density"],
    "electronic_conductivity": ["ElectronicConductivity"],
    "electrolyte_conductivity_function": ["IonicConductivity"],
    "exchange_current_density_function": ["ExchangeCurrentDensity"],
    "initial_temperature": ["InititalThermodynamicTemperature"],
    "lithium_diffusion_coefficient_function": ["Diffusivity"],
    "lithium_diffusivity": ["Diffusivity"],
    "lithium_stoichiometric_coefficient_at_soc_0": ["StoichiometricCoefficientAtSOC0", "StoichiometricCoefficient"],
    "lithium_stoichiometric_coefficient_at_soc_100": ["StoichiometricCoefficientAtSOC100", "StoichiometricCoefficient"],
    "lithium_transference_number": ["IonTransportNumber"],
    "lower_cutoff_voltage": ["LowerVoltageLimit"],
    "mass_fraction": ["MassFraction"],
    "maximum_lithium_concentration": ["MaximumConcentration"],
    "number_of_electrons_transferred": ["NumberOfElectronsTransferred"],
    "open_circuit_voltage_function": ["OpenCircuitVoltage"],
    "particle_radius": ["ParticleRadius"],
    "porosity": ["Porosity"],
    "reaction_rate_constant": ["ReactionRateConstant"],
    "specific_heat_capacity": ["SpecificHeatCapacity"],
    "thermal_conductivity": ["ThermalConductivity"],
    "thickness": ["Thickness"],
    "volumetric_surface_area": ["VolumetricSurfaceArea"],
    "volume_fraction": ["VolumeFraction"],
}

LEGACY_PROPERTY_BINDINGS = {
    ("specification", "property", "initial_temperature"): {
        "label": "InitialTemperature",
        "model_type": "electrochemistry:electrochemistry_9c9b80a4_a00b_4b91_8e17_3a7831f2bf2f",
    },
    ("specification", "property", "lower_cutoff_voltage"): {
        "label": "LowerCutoffVoltage",
        "model_type": "electrochemistry:electrochemistry_534dd59c_904c_45d9_8550_ae9d2eb6bbc9",
    },
    ("specification", "separator", "property", "thickness"): {
        "label": "SeparatorThickness",
        "model_type": ":modellib_47288277_4aed_447e_b659_0c975d031406",
    },
    ("specification", "separator", "property", "porosity"): {
        "label": "SeparatorPorosity",
        "model_type": ":modellib_a4858e4d_dd3b_48ce_97ba_3eeb8571b633",
    },
    ("specification", "electrolyte", "salt", "property", "concentration"): {
        "label": "InitialLithiumConcentrationInElectrolyte",
        "model_type": ":modellib_098f98dc_e015_4dbd_b358_a7ac3b3ecff3",
    },
    ("specification", "electrolyte", "property", "electrolyte_conductivity_function"): {
        "label": "ElectrolyteConductivity",
        "model_type": ":modellib_1923575e_05b0_4b8b_8d58_0b2f2ba41c3e",
    },
    ("specification", "electrolyte", "property", "lithium_diffusion_coefficient_function"): {
        "label": "LithiumDiffusivityInElectrolyte",
        "model_type": ":modellib_4c274506_af5b_4ef1_8217_829ffd459f28",
    },
    ("specification", "electrolyte", "property", "lithium_transference_number"): {
        "label": "LithiumTransportNumber",
        "model_type": ":modellib_e3e78df2_d568_4ab7_8c0d_d3a2ee3ae282",
    },
    ("specification", "positive_electrode", "coating", "property", "thickness"): {
        "label": "PositiveElectrodeCoatingThickness",
        "model_type": ":modellib_62f5beeb_6d1e_442a_8048_3ebe08882964",
    },
    ("specification", "positive_electrode", "coating", "property", "porosity"): {
        "label": "PositiveElectrodeCoatingPorosity",
        "model_type": ":modellib_7481c4c9_c247_4248_a045_a1077230acba",
    },
    ("specification", "positive_electrode", "coating", "property", "electronic_conductivity"): {
        "label": "PositiveElectrodeElectronicConductivity",
        "model_type": ":modellib_43f77743_1af6_4a0f_9cc6_285c2a450549",
    },
    ("specification", "positive_electrode", "coating", "component", "active_material", 0, "property", "particle_radius"): {
        "label": "PositiveElectrodeActiveMaterialParticleRadius",
        "model_type": ":modellib_58400817_3282_46e5_942e_3a1538631403",
    },
    (
        "specification",
        "positive_electrode",
        "coating",
        "component",
        "active_material",
        0,
        "property",
        "maximum_lithium_concentration",
    ): {
        "label": "PositiveElectrodeMaximumLithiumConcentration",
        "model_type": ":modellib_c69a9d55_823f_4113_a305_ebc89dde7de3",
    },
    ("specification", "positive_electrode", "coating", "component", "active_material", 0, "property", "lithium_diffusivity"): {
        "label": "LithiumDiffusivityInPositiveElectrode",
        "model_type": ":modellib_e59188bb_ce66_49f6_84aa_ecb98e76941e",
    },
    (
        "specification",
        "positive_electrode",
        "coating",
        "component",
        "active_material",
        0,
        "property",
        "activation_energy_of_lithium_diffusivity",
    ): {
        "label": "ActivationEnergyOfLithiumDiffusivityInPositiveElectrode",
        "model_type": ":modellib_4d69edda_d2fa_40b0_9c1e_52e08debf578",
    },
    ("specification", "positive_electrode", "coating", "component", "active_material", 0, "property", "volumetric_surface_area"): {
        "label": "PositiveElectrodeActiveMaterialVolumetricSurfaceArea",
        "model_type": ":modellib_0a1e73c5_e91b_4365_88d4_1e1f476bf776",
    },
    (
        "specification",
        "positive_electrode",
        "coating",
        "component",
        "active_material",
        0,
        "property",
        "lithium_stoichiometric_coefficient_at_soc_0",
    ): {
        "label": "PositiveElectrodeLithiumStoichiometricCoefficientAtSOC0",
        "model_type": ":modellib_80920875_62ac_4e29_b970_ec4316e76aa5",
    },
    (
        "specification",
        "positive_electrode",
        "coating",
        "component",
        "active_material",
        0,
        "property",
        "lithium_stoichiometric_coefficient_at_soc_100",
    ): {
        "label": "PositiveElectrodeLithiumStoichiometricCoefficientAtSOC100",
        "model_type": ":modellib_99041897_5c08_40ed_9118_3e77e9b0e191",
    },
    (
        "specification",
        "positive_electrode",
        "coating",
        "component",
        "active_material",
        0,
        "property",
        "open_circuit_voltage_function",
    ): {
        "label": "PositiveElectrodeActiveMaterialOpenCircuitVoltage",
        "model_type": ":modellib_52ab4fdd_f945_4541_9ce6_cd6fd3a05861",
    },
    ("specification", "positive_electrode", "coating", "component", "active_material", 0, "property", "reaction_rate_constant"): {
        "label": "PositiveElectrodeReactionRateConstant",
        "model_type": ":modellib_404126e0_cb1b_44e4_98dc_2474185767a1",
    },
    (
        "specification",
        "positive_electrode",
        "coating",
        "component",
        "active_material",
        0,
        "property",
        "activation_energy_of_reaction",
    ): {
        "label": "PositiveElectrodeActivationEnergyOfReaction",
        "model_type": ":modellib_56b9cd1f_5397_4385_9292_30d93d9e7a05",
    },
    ("specification", "negative_electrode", "coating", "property", "thickness"): {
        "label": "NegativeElectrodeCoatingThickness",
        "model_type": ":modellib_cdc91ec0_9fc5_4551_bbd9_6824c2920124",
    },
    ("specification", "negative_electrode", "coating", "property", "porosity"): {
        "label": "NegativeElectrodeCoatingPorosity",
        "model_type": ":modellib_5cb403c4_4f28_46cb_81c4_21c5c47ef14a",
    },
    ("specification", "negative_electrode", "coating", "property", "electronic_conductivity"): {
        "label": "NegativeElectrodeElectronicConductivity",
        "model_type": ":modellib_be3da3e2_58a9_4e58_adc2_7336d312717c",
    },
    ("specification", "negative_electrode", "coating", "component", "active_material", 0, "property", "particle_radius"): {
        "label": "NegativeElectrodeActiveMaterialParticleRadius",
        "model_type": ":modellib_bfe553c2_a63e_49b6_a209_0855dfc39724",
    },
    (
        "specification",
        "negative_electrode",
        "coating",
        "component",
        "active_material",
        0,
        "property",
        "maximum_lithium_concentration",
    ): {
        "label": "NegativeElectrodeMaximumLithiumConcentration",
        "model_type": ":modellib_e808a26a_5812_49e9_894c_b793c7fe0c38",
    },
    ("specification", "negative_electrode", "coating", "component", "active_material", 0, "property", "lithium_diffusivity"): {
        "label": "LithiumDiffusivityInNegativeElectrode",
        "model_type": ":modellib_50247e71_75fe_4986_959e_fd06c6be98db",
    },
    (
        "specification",
        "negative_electrode",
        "coating",
        "component",
        "active_material",
        0,
        "property",
        "activation_energy_of_lithium_diffusivity",
    ): {
        "label": "ActivationEnergyOfLithiumDiffusivityInNegativeElectrode",
        "model_type": ":modellib_86af4487_33c1_4562_a00b_3a8252ffe378",
    },
    ("specification", "negative_electrode", "coating", "component", "active_material", 0, "property", "volumetric_surface_area"): {
        "label": "NegativeElectrodeActiveMaterialVolumetricSurfaceArea",
        "model_type": ":modellib_c5f9b91e_a770_4e9b_837e_fa2a76019111",
    },
    (
        "specification",
        "negative_electrode",
        "coating",
        "component",
        "active_material",
        0,
        "property",
        "lithium_stoichiometric_coefficient_at_soc_0",
    ): {
        "label": "NegativeElectrodeLithiumStoichiometricCoefficientAtSOC0",
        "model_type": ":modellib_21da0fe9_9fb6_4840_a12f_fbcc1ba84fb3",
    },
    (
        "specification",
        "negative_electrode",
        "coating",
        "component",
        "active_material",
        0,
        "property",
        "lithium_stoichiometric_coefficient_at_soc_100",
    ): {
        "label": "NegativeElectrodeLithiumStoichiometricCoefficientAtSOC100",
        "model_type": ":modellib_8c336ae9_1818_4b08_a660_4bb83b28351f",
    },
    (
        "specification",
        "negative_electrode",
        "coating",
        "component",
        "active_material",
        0,
        "property",
        "open_circuit_voltage_function",
    ): {
        "label": "NegativeElectrodeActiveMaterialOpenCircuitVoltage",
        "model_type": ":modellib_0e2f4fe6_570a_4d13_81e9_de1d4f9987af",
    },
}


def resolve_battinfo_root() -> Path:
    for env_var in BATTINFO_ENV_VARS:
        value = os.environ.get(env_var)
        if value:
            candidate = Path(value).expanduser()
            if (candidate / "src" / "battinfo").is_dir():
                return candidate
    if (DEFAULT_BATTINFO_ROOT / "src" / "battinfo").is_dir():
        return DEFAULT_BATTINFO_ROOT
    raise FileNotFoundError(
        "Could not locate a BattINFO checkout. Set BATTINFO_DIR, BATTINFO_ROOT, or BATTINFO_REPO."
    )


def ensure_battinfo_runtime() -> tuple[Any, Any, Any]:
    battinfo_root = resolve_battinfo_root()
    battinfo_src = battinfo_root / "src"
    if str(battinfo_src) not in sys.path:
        sys.path.insert(0, str(battinfo_src))

    try:
        from battinfo.transform.json_to_jsonld import to_jsonld
        from battinfo.validate.jsonld import validate_jsonld
        from battinfo.validate.pydantic import validate_json
    except ModuleNotFoundError:
        battinfo_python = battinfo_root / ".venv" / "Scripts" / "python.exe"
        if battinfo_python.is_file() and Path(sys.executable).resolve() != battinfo_python.resolve():
            env = dict(os.environ)
            env["PYTHONPATH"] = str(battinfo_src) + os.pathsep + env.get("PYTHONPATH", "")
            subprocess.run([str(battinfo_python), __file__, *sys.argv[1:]], check=True, env=env)
            raise SystemExit(0)
        raise

    return to_jsonld, validate_json, validate_jsonld


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def quantity(*, value: float | int | str | None = None, unit: str, value_text: str | None = None) -> dict[str, Any]:
    data: dict[str, Any] = {"unit": unit}
    if value_text is not None:
        data["value_text"] = value_text
    else:
        data["value"] = value
    return data


def timestamp_now() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def camel_case_label(name: str) -> str:
    return "".join(part[:1].upper() + part[1:] for part in name.split("_"))


def pluralize(items: list[dict[str, Any]]) -> dict[str, Any] | list[dict[str, Any]] | None:
    if not items:
        return None
    return items[0] if len(items) == 1 else items


def add_unique_type(node: dict[str, Any], new_type: str) -> None:
    current = node.get("@type")
    if current is None:
        node["@type"] = new_type
        return
    if isinstance(current, str):
        if current != new_type:
            node["@type"] = [current, new_type]
        return
    if isinstance(current, list) and new_type not in current:
        node["@type"] = [*current, new_type]


def normalize_model_type(value: str) -> str:
    if value.startswith(":modellib_"):
        return f"model:{value[1:]}"
    return value


def property_types(property_name: str, *, source_path: tuple[Any, ...], is_coating_property: bool = False) -> list[str]:
    types = list(GENERIC_PROPERTY_TYPES.get(property_name, []))
    if is_coating_property and property_name == "thickness":
        types = ["CalenderedCoatingThickness", "CoatingThickness", *types]
    return list(dict.fromkeys(types))


def build_property_node(
    property_name: str,
    quantity_data: dict[str, Any],
    *,
    source_path: tuple[Any, ...],
    is_coating_property: bool = False,
) -> dict[str, Any]:
    metadata = LEGACY_PROPERTY_BINDINGS.get(source_path, {})
    node_types = property_types(property_name, source_path=source_path, is_coating_property=is_coating_property)
    node_types.append("ConventionalProperty")
    model_type = metadata.get("model_type")
    if isinstance(model_type, str):
        node_types.append(normalize_model_type(model_type))
    node_types = list(dict.fromkeys(node_types))

    node: dict[str, Any] = {
        "@type": node_types[0] if len(node_types) == 1 else node_types,
        "rdfs:label": metadata.get("label", camel_case_label(property_name)),
    }

    if "value_text" in quantity_data:
        node["hasPart"] = {
            "@type": "String",
            "hasStringValue": quantity_data["value_text"],
        }
    else:
        node["hasNumericalPart"] = {
            "@type": "emmo:RealData",
            "hasNumberValue": quantity_data["value"],
        }

    unit = quantity_data.get("unit") or quantity_data.get("unit_text")
    if isinstance(unit, str) and unit:
        unit_iri = UNIT_IRIS.get(unit)
        if unit_iri is not None:
            node["hasMeasurementUnit"] = unit_iri
        else:
            node["schema:unitText"] = unit

    return node


def assign_measured_properties(
    target_node: dict[str, Any] | None,
    properties: dict[str, Any] | None,
    *,
    source_prefix: tuple[Any, ...],
    is_coating_property: bool = False,
) -> None:
    if not isinstance(target_node, dict) or not isinstance(properties, dict):
        return
    property_nodes = [
        build_property_node(
            property_name,
            quantity_data,
            source_path=(*source_prefix, property_name),
            is_coating_property=is_coating_property,
        )
        for property_name, quantity_data in properties.items()
        if isinstance(quantity_data, dict)
    ]
    property_nodes = [node for node in property_nodes if node]
    if property_nodes:
        target_node["hasMeasuredProperty"] = pluralize(property_nodes)
    else:
        target_node.pop("hasMeasuredProperty", None)


def first_dict(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                return item
    return None


def dict_list(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def attach_component_properties(jsonld_doc: dict[str, Any], descriptor: dict[str, Any]) -> None:
    specification = descriptor["specification"]
    assign_measured_properties(
        jsonld_doc,
        specification.get("property"),
        source_prefix=("specification", "property"),
    )

    positive_electrode = first_dict(jsonld_doc.get("hasPositiveElectrode"))
    positive_source = specification.get("positive_electrode", {})
    assign_measured_properties(
        positive_electrode,
        positive_source.get("property"),
        source_prefix=("specification", "positive_electrode", "property"),
    )
    positive_coating_node = first_dict(positive_electrode.get("hasCoating")) if positive_electrode else None
    assign_measured_properties(
        positive_coating_node,
        positive_source.get("coating", {}).get("property"),
        source_prefix=("specification", "positive_electrode", "coating", "property"),
        is_coating_property=True,
    )
    positive_component_source = positive_source.get("coating", {}).get("component", {})
    for index, material_node in enumerate(dict_list(positive_coating_node.get("hasActiveMaterial")) if positive_coating_node else []):
        material_source = positive_component_source.get("active_material", [])[index]
        assign_measured_properties(
            material_node,
            material_source.get("property"),
            source_prefix=("specification", "positive_electrode", "coating", "component", "active_material", index, "property"),
        )
    for index, binder_node in enumerate(dict_list(positive_coating_node.get("hasBinder")) if positive_coating_node else []):
        binder_source = positive_component_source.get("binder", [])[index]
        assign_measured_properties(
            binder_node,
            binder_source.get("property"),
            source_prefix=("specification", "positive_electrode", "coating", "component", "binder", index, "property"),
        )
    for index, additive_node in enumerate(
        dict_list(positive_coating_node.get("hasConductiveAdditive")) if positive_coating_node else []
    ):
        additive_source = positive_component_source.get("additive", [])[index]
        assign_measured_properties(
            additive_node,
            additive_source.get("property"),
            source_prefix=("specification", "positive_electrode", "coating", "component", "additive", index, "property"),
        )
    assign_measured_properties(
        first_dict(positive_electrode.get("hasCurrentCollector")) if positive_electrode else None,
        positive_source.get("current_collector", {}).get("property"),
        source_prefix=("specification", "positive_electrode", "current_collector", "property"),
    )

    negative_electrode = first_dict(jsonld_doc.get("hasNegativeElectrode"))
    negative_source = specification.get("negative_electrode", {})
    assign_measured_properties(
        negative_electrode,
        negative_source.get("property"),
        source_prefix=("specification", "negative_electrode", "property"),
    )
    negative_coating_node = first_dict(negative_electrode.get("hasCoating")) if negative_electrode else None
    assign_measured_properties(
        negative_coating_node,
        negative_source.get("coating", {}).get("property"),
        source_prefix=("specification", "negative_electrode", "coating", "property"),
        is_coating_property=True,
    )
    negative_component_source = negative_source.get("coating", {}).get("component", {})
    for index, material_node in enumerate(dict_list(negative_coating_node.get("hasActiveMaterial")) if negative_coating_node else []):
        material_source = negative_component_source.get("active_material", [])[index]
        assign_measured_properties(
            material_node,
            material_source.get("property"),
            source_prefix=("specification", "negative_electrode", "coating", "component", "active_material", index, "property"),
        )
    for index, binder_node in enumerate(dict_list(negative_coating_node.get("hasBinder")) if negative_coating_node else []):
        binder_source = negative_component_source.get("binder", [])[index]
        assign_measured_properties(
            binder_node,
            binder_source.get("property"),
            source_prefix=("specification", "negative_electrode", "coating", "component", "binder", index, "property"),
        )
    for index, additive_node in enumerate(
        dict_list(negative_coating_node.get("hasConductiveAdditive")) if negative_coating_node else []
    ):
        additive_source = negative_component_source.get("additive", [])[index]
        assign_measured_properties(
            additive_node,
            additive_source.get("property"),
            source_prefix=("specification", "negative_electrode", "coating", "component", "additive", index, "property"),
        )
    assign_measured_properties(
        first_dict(negative_electrode.get("hasCurrentCollector")) if negative_electrode else None,
        negative_source.get("current_collector", {}).get("property"),
        source_prefix=("specification", "negative_electrode", "current_collector", "property"),
    )

    electrolyte_node = first_dict(jsonld_doc.get("hasElectrolyte"))
    electrolyte_source = specification.get("electrolyte", {})
    assign_measured_properties(
        electrolyte_node,
        electrolyte_source.get("property"),
        source_prefix=("specification", "electrolyte", "property"),
    )
    solute_node = first_dict(electrolyte_node.get("hasSolute")) if electrolyte_node else None
    assign_measured_properties(
        first_dict(solute_node.get("hasConstituent")) if solute_node else None,
        electrolyte_source.get("salt", {}).get("property"),
        source_prefix=("specification", "electrolyte", "salt", "property"),
    )
    additive_wrapper = first_dict(solute_node.get("hasAdditive")) if solute_node else None
    for index, additive_node in enumerate(dict_list(additive_wrapper.get("hasConstituent")) if additive_wrapper else []):
        additive_source = electrolyte_source.get("additive", [])[index]
        assign_measured_properties(
            additive_node,
            additive_source.get("property"),
            source_prefix=("specification", "electrolyte", "additive", index, "property"),
        )

    separator_node = first_dict(jsonld_doc.get("hasSeparator"))
    assign_measured_properties(
        separator_node,
        specification.get("separator", {}).get("property"),
        source_prefix=("specification", "separator", "property"),
    )


def enrich_root_metadata(jsonld_doc: dict[str, Any], descriptor: dict[str, Any]) -> None:
    specification = descriptor["specification"]
    add_unique_type(jsonld_doc, "BatteryCell")
    contexts = jsonld_doc.get("@context")
    if isinstance(contexts, list) and len(contexts) > 1 and isinstance(contexts[1], dict):
        contexts[1]["model"] = "https://w3id.org/emmo/domain/battery-model-lithium-ion#"
    jsonld_doc["@id"] = specification["id"]
    jsonld_doc["schema:model"] = specification["model"]
    jsonld_doc["schema:name"] = specification["model"]

    provenance = descriptor.get("provenance")
    if not isinstance(provenance, dict):
        return

    source_node: dict[str, Any] = {"@type": "schema:CreativeWork"}
    if provenance.get("source_url"):
        source_node["@id"] = provenance["source_url"]
        source_node["schema:url"] = provenance["source_url"]
    if provenance.get("source_name"):
        source_node["schema:name"] = provenance["source_name"]
    if provenance.get("source_file"):
        source_node["schema:identifier"] = provenance["source_file"]
    if provenance.get("workflow_version"):
        source_node["schema:version"] = provenance["workflow_version"]
    if provenance.get("comment"):
        source_node["schema:description"] = provenance["comment"]
    if provenance.get("retrieved_at"):
        source_node["schema:dateModified"] = datetime.fromtimestamp(
            provenance["retrieved_at"], tz=timezone.utc
        ).isoformat()
    if len(source_node) > 1:
        jsonld_doc["schema:isBasedOn"] = source_node

    citation = provenance.get("citation")
    if citation:
        jsonld_doc["schema:citation"] = {"@id": citation}


def build_descriptor() -> dict[str, Any]:
    base = load_json(ROOT / "parameters" / "h0b-base.json")
    equilibrium = load_json(ROOT / "parameters" / "equilibrium-calibration-parameters.json")
    high_rate = load_json(ROOT / "parameters" / "high-rate-calibration-parameters.json")

    positive_volume_fraction = equilibrium["PositiveElectrode"]["Coating"]["volumeFraction"]
    negative_volume_fraction = equilibrium["NegativeElectrode"]["Coating"]["volumeFraction"]

    return {
        "schema_version": "1.0.0",
        "specification": {
            "id": "https://w3id.org/battinfo/cell-type/7mp5-7012-0h0b-sc26",
            "manufacturer": "Unknown",
            "model": "IMP5-70-120-H0B",
            "format": "pouch",
            "chemistry": "Li-ion",
            "positive_electrode_basis": "LNMO",
            "negative_electrode_basis": "graphite",
            "construction": {
                "assembly_type": "stacked",
                "layering": "single_layer",
                "layer_count": 1,
                "assembly_sequence": ["positive electrode", "separator", "negative electrode"],
            },
            "property": {
                "initial_temperature": quantity(value=base["initT"], unit="K"),
                "lower_cutoff_voltage": quantity(value=base["Control"]["lowerCutoffVoltage"], unit="V"),
            },
            "positive_electrode": {
                "coating": {
                    "component": {
                        "active_material": [
                            {
                                "name": "LNMO",
                                "property": {
                                    "mass_fraction": quantity(
                                        value=base["PositiveElectrode"]["Coating"]["ActiveMaterial"]["massFraction"], unit="1"
                                    ),
                                    "density": quantity(
                                        value=base["PositiveElectrode"]["Coating"]["ActiveMaterial"]["density"], unit="kg/m^3"
                                    ),
                                    "particle_radius": quantity(
                                        value=base["PositiveElectrode"]["Coating"]["ActiveMaterial"]["SolidDiffusion"][
                                            "particleRadius"
                                        ],
                                        unit="m",
                                    ),
                                    "maximum_lithium_concentration": quantity(
                                        value=base["PositiveElectrode"]["Coating"]["ActiveMaterial"]["Interface"][
                                            "saturationConcentration"
                                        ],
                                        unit="mol/m^3",
                                    ),
                                    "lithium_diffusivity": quantity(
                                        value=high_rate["PositiveElectrode"]["Coating"]["ActiveMaterial"]["SolidDiffusion"][
                                            "referenceDiffusionCoefficient"
                                        ],
                                        unit="m^2/s",
                                    ),
                                    "activation_energy_of_lithium_diffusivity": quantity(
                                        value=base["PositiveElectrode"]["Coating"]["ActiveMaterial"]["SolidDiffusion"][
                                            "activationEnergyOfDiffusion"
                                        ],
                                        unit="J/mol",
                                    ),
                                    "volumetric_surface_area": quantity(
                                        value=high_rate["PositiveElectrode"]["Coating"]["ActiveMaterial"]["Interface"][
                                            "volumetricSurfaceArea"
                                        ],
                                        unit="1/m",
                                    ),
                                    "lithium_stoichiometric_coefficient_at_soc_0": quantity(
                                        value=equilibrium["PositiveElectrode"]["Coating"]["ActiveMaterial"]["Interface"][
                                            "guestStoichiometry0"
                                        ],
                                        unit="1",
                                    ),
                                    "lithium_stoichiometric_coefficient_at_soc_100": quantity(
                                        value=equilibrium["PositiveElectrode"]["Coating"]["ActiveMaterial"]["Interface"][
                                            "guestStoichiometry100"
                                        ],
                                        unit="1",
                                    ),
                                    "open_circuit_voltage_function": quantity(
                                        value_text=base["PositiveElectrode"]["Coating"]["ActiveMaterial"]["Interface"][
                                            "openCircuitPotential"
                                        ]["functionName"],
                                        unit="V",
                                    ),
                                    "reaction_rate_constant": quantity(
                                        value=base["PositiveElectrode"]["Coating"]["ActiveMaterial"]["Interface"][
                                            "reactionRateConstant"
                                        ],
                                        unit="mol/m^2/s",
                                    ),
                                    "activation_energy_of_reaction": quantity(
                                        value=base["PositiveElectrode"]["Coating"]["ActiveMaterial"]["Interface"][
                                            "activationEnergyOfReaction"
                                        ],
                                        unit="J/mol",
                                    ),
                                    "charge_transfer_coefficient": quantity(
                                        value=base["PositiveElectrode"]["Coating"]["ActiveMaterial"]["Interface"][
                                            "chargeTransferCoefficient"
                                        ],
                                        unit="1",
                                    ),
                                    "number_of_electrons_transferred": quantity(
                                        value=base["PositiveElectrode"]["Coating"]["ActiveMaterial"]["Interface"][
                                            "numberOfElectronsTransferred"
                                        ],
                                        unit="1",
                                    ),
                                },
                                "comment": "Positive-electrode active material block for the calibrated LNMO parameterization.",
                            }
                        ],
                        "binder": [
                            {
                                "name": "PVDF",
                                "property": {
                                    "mass_fraction": quantity(
                                        value=base["PositiveElectrode"]["Coating"]["Binder"]["massFraction"], unit="1"
                                    ),
                                    "density": quantity(
                                        value=base["PositiveElectrode"]["Coating"]["Binder"]["density"], unit="kg/m^3"
                                    ),
                                    "electronic_conductivity": quantity(
                                        value=base["PositiveElectrode"]["Coating"]["Binder"]["electronicConductivity"],
                                        unit="S/m",
                                    ),
                                },
                            }
                        ],
                        "additive": [
                            {
                                "name": "Carbon black",
                                "property": {
                                    "mass_fraction": quantity(
                                        value=base["PositiveElectrode"]["Coating"]["ConductingAdditive"]["massFraction"],
                                        unit="1",
                                    ),
                                    "density": quantity(
                                        value=base["PositiveElectrode"]["Coating"]["ConductingAdditive"]["density"],
                                        unit="kg/m^3",
                                    ),
                                    "electronic_conductivity": quantity(
                                        value=base["PositiveElectrode"]["Coating"]["ConductingAdditive"][
                                            "electronicConductivity"
                                        ],
                                        unit="S/m",
                                    ),
                                },
                            }
                        ],
                    },
                    "property": {
                        "thickness": quantity(value=base["PositiveElectrode"]["Coating"]["thickness"], unit="m"),
                        "porosity": quantity(value=1.0 - positive_volume_fraction, unit="1"),
                        "volume_fraction": quantity(value=positive_volume_fraction, unit="1"),
                        "electronic_conductivity": quantity(
                            value=base["PositiveElectrode"]["Coating"]["electronicConductivity"], unit="S/m"
                        ),
                        "bruggeman_coefficient": quantity(
                            value=high_rate["PositiveElectrode"]["Coating"]["bruggemanCoefficient"], unit="1"
                        ),
                        "electrolyte_bruggeman_coefficient": quantity(
                            value=high_rate["Electrolyte"]["regionBruggemanCoefficients"]["PositiveElectrode"], unit="1"
                        ),
                    },
                    "comment": "Positive-electrode coating properties after equilibrium and high-rate calibration.",
                },
                "current_collector": {
                    "name": "Al foil",
                    "property": {
                        "thickness": quantity(
                            value=base["PositiveElectrode"]["CurrentCollector"]["thickness"], unit="m"
                        ),
                        "electronic_conductivity": quantity(
                            value=base["PositiveElectrode"]["CurrentCollector"]["electronicConductivity"], unit="S/m"
                        ),
                        "thermal_conductivity": quantity(
                            value=base["PositiveElectrode"]["CurrentCollector"]["thermalConductivity"], unit="W/m/K"
                        ),
                        "specific_heat_capacity": quantity(
                            value=base["PositiveElectrode"]["CurrentCollector"]["specificHeatCapacity"], unit="J/kg/K"
                        ),
                        "density": quantity(
                            value=base["PositiveElectrode"]["CurrentCollector"]["density"], unit="kg/m^3"
                        ),
                    },
                    "comment": base["PositiveElectrode"]["CurrentCollector"]["comment"],
                },
            },
            "negative_electrode": {
                "coating": {
                    "component": {
                        "active_material": [
                            {
                                "name": "Graphite",
                                "property": {
                                    "mass_fraction": quantity(
                                        value=base["NegativeElectrode"]["Coating"]["ActiveMaterial"]["massFraction"], unit="1"
                                    ),
                                    "density": quantity(
                                        value=base["NegativeElectrode"]["Coating"]["ActiveMaterial"]["density"], unit="kg/m^3"
                                    ),
                                    "particle_radius": quantity(
                                        value=base["NegativeElectrode"]["Coating"]["ActiveMaterial"]["SolidDiffusion"][
                                            "particleRadius"
                                        ],
                                        unit="m",
                                    ),
                                    "maximum_lithium_concentration": quantity(
                                        value=base["NegativeElectrode"]["Coating"]["ActiveMaterial"]["Interface"][
                                            "saturationConcentration"
                                        ],
                                        unit="mol/m^3",
                                    ),
                                    "lithium_diffusivity": quantity(
                                        value=high_rate["NegativeElectrode"]["Coating"]["ActiveMaterial"]["SolidDiffusion"][
                                            "referenceDiffusionCoefficient"
                                        ],
                                        unit="m^2/s",
                                    ),
                                    "activation_energy_of_lithium_diffusivity": quantity(
                                        value=base["NegativeElectrode"]["Coating"]["ActiveMaterial"]["SolidDiffusion"][
                                            "activationEnergyOfDiffusion"
                                        ],
                                        unit="J/mol",
                                    ),
                                    "volumetric_surface_area": quantity(
                                        value=high_rate["NegativeElectrode"]["Coating"]["ActiveMaterial"]["Interface"][
                                            "volumetricSurfaceArea"
                                        ],
                                        unit="1/m",
                                    ),
                                    "lithium_stoichiometric_coefficient_at_soc_0": quantity(
                                        value=equilibrium["NegativeElectrode"]["Coating"]["ActiveMaterial"]["Interface"][
                                            "guestStoichiometry0"
                                        ],
                                        unit="1",
                                    ),
                                    "lithium_stoichiometric_coefficient_at_soc_100": quantity(
                                        value=equilibrium["NegativeElectrode"]["Coating"]["ActiveMaterial"]["Interface"][
                                            "guestStoichiometry100"
                                        ],
                                        unit="1",
                                    ),
                                    "open_circuit_voltage_function": quantity(
                                        value_text=base["NegativeElectrode"]["Coating"]["ActiveMaterial"]["Interface"][
                                            "openCircuitPotential"
                                        ]["functionName"],
                                        unit="V",
                                    ),
                                    "exchange_current_density_function": quantity(
                                        value_text=base["NegativeElectrode"]["Coating"]["ActiveMaterial"]["Interface"][
                                            "exchangeCurrentDensity"
                                        ]["functionName"],
                                        unit="A/m^2",
                                    ),
                                    "charge_transfer_coefficient": quantity(
                                        value=base["NegativeElectrode"]["Coating"]["ActiveMaterial"]["Interface"][
                                            "chargeTransferCoefficient"
                                        ],
                                        unit="1",
                                    ),
                                    "number_of_electrons_transferred": quantity(
                                        value=base["NegativeElectrode"]["Coating"]["ActiveMaterial"]["Interface"][
                                            "numberOfElectronsTransferred"
                                        ],
                                        unit="1",
                                    ),
                                },
                                "comment": "Negative-electrode active material block for the calibrated graphite parameterization.",
                            }
                        ],
                        "binder": [
                            {
                                "name": "Binder",
                                "property": {
                                    "mass_fraction": quantity(
                                        value=base["NegativeElectrode"]["Coating"]["Binder"]["massFraction"], unit="1"
                                    ),
                                    "density": quantity(
                                        value=base["NegativeElectrode"]["Coating"]["Binder"]["density"], unit="kg/m^3"
                                    ),
                                    "electronic_conductivity": quantity(
                                        value=base["NegativeElectrode"]["Coating"]["Binder"]["electronicConductivity"],
                                        unit="S/m",
                                    ),
                                },
                            }
                        ],
                        "additive": [
                            {
                                "name": "Carbon black",
                                "property": {
                                    "mass_fraction": quantity(
                                        value=base["NegativeElectrode"]["Coating"]["ConductingAdditive"]["massFraction"],
                                        unit="1",
                                    ),
                                    "density": quantity(
                                        value=base["NegativeElectrode"]["Coating"]["ConductingAdditive"]["density"],
                                        unit="kg/m^3",
                                    ),
                                    "electronic_conductivity": quantity(
                                        value=base["NegativeElectrode"]["Coating"]["ConductingAdditive"][
                                            "electronicConductivity"
                                        ],
                                        unit="S/m",
                                    ),
                                },
                            }
                        ],
                    },
                    "property": {
                        "thickness": quantity(value=base["NegativeElectrode"]["Coating"]["thickness"], unit="m"),
                        "porosity": quantity(value=1.0 - negative_volume_fraction, unit="1"),
                        "volume_fraction": quantity(value=negative_volume_fraction, unit="1"),
                        "electronic_conductivity": quantity(
                            value=base["NegativeElectrode"]["Coating"]["electronicConductivity"], unit="S/m"
                        ),
                        "bruggeman_coefficient": quantity(
                            value=high_rate["NegativeElectrode"]["Coating"]["bruggemanCoefficient"], unit="1"
                        ),
                        "electrolyte_bruggeman_coefficient": quantity(
                            value=high_rate["Electrolyte"]["regionBruggemanCoefficients"]["NegativeElectrode"], unit="1"
                        ),
                    },
                    "comment": "Negative-electrode coating properties after equilibrium and high-rate calibration.",
                },
                "current_collector": {
                    "name": "Cu foil",
                    "property": {
                        "thickness": quantity(
                            value=base["NegativeElectrode"]["CurrentCollector"]["thickness"], unit="m"
                        ),
                        "electronic_conductivity": quantity(
                            value=base["NegativeElectrode"]["CurrentCollector"]["electronicConductivity"], unit="S/m"
                        ),
                        "thermal_conductivity": quantity(
                            value=base["NegativeElectrode"]["CurrentCollector"]["thermalConductivity"], unit="W/m/K"
                        ),
                        "specific_heat_capacity": quantity(
                            value=base["NegativeElectrode"]["CurrentCollector"]["specificHeatCapacity"], unit="J/kg/K"
                        ),
                        "density": quantity(
                            value=base["NegativeElectrode"]["CurrentCollector"]["density"], unit="kg/m^3"
                        ),
                    },
                    "comment": base["NegativeElectrode"]["CurrentCollector"]["comment"],
                },
            },
            "electrolyte": {
                "family": "organic",
                "salt": {
                    "name": "LiPF6",
                    "cation": "Li+",
                    "anion": "PF6-",
                    "property": {
                        "concentration": quantity(
                            value=base["Electrolyte"]["species"]["nominalConcentration"], unit="mol/m^3"
                        ),
                        "charge_number": quantity(value=base["Electrolyte"]["species"]["chargeNumber"], unit="1"),
                    },
                },
                "property": {
                    "density": quantity(value=base["Electrolyte"]["density"], unit="kg/m^3"),
                    "lithium_transference_number": quantity(
                        value=base["Electrolyte"]["species"]["transferenceNumber"], unit="1"
                    ),
                    "lithium_diffusion_coefficient_function": quantity(
                        value_text=base["Electrolyte"]["diffusionCoefficient"]["functionName"], unit="m^2/s"
                    ),
                    "electrolyte_conductivity_function": quantity(
                        value_text=base["Electrolyte"]["ionicConductivity"]["functionName"], unit="S/m"
                    ),
                    "bulk_bruggeman_coefficient": quantity(
                        value=base["Electrolyte"]["bruggemanCoefficient"], unit="1"
                    ),
                },
                "comment": "Electrolyte block captures the bulk electrolyte parameterization and the conducting salt metadata.",
            },
            "separator": {
                "material": "Unspecified polyolefin separator",
                "property": {
                    "thickness": quantity(value=base["Separator"]["thickness"], unit="m"),
                    "porosity": quantity(value=base["Separator"]["porosity"], unit="1"),
                    "density": quantity(value=base["Separator"]["density"], unit="kg/m^3"),
                    "bruggeman_coefficient": quantity(value=base["Separator"]["bruggemanCoefficient"], unit="1"),
                    "electrolyte_bruggeman_coefficient": quantity(
                        value=high_rate["Electrolyte"]["regionBruggemanCoefficients"]["Separator"], unit="1"
                    ),
                },
            },
            "comment": [
                "BattINFO-style cell descriptor derived from the published BattMo parameter files.",
                "Quantities are attached to the battery cell, its components, and material constituents rather than flattened into a single property list.",
            ],
        },
        "provenance": {
            "source_type": "derived",
            "source_name": "Graphite/LNMO BattMo publication workflow",
            "source_file": "scripts/generate_optimization_linked_data.py",
            "source_url": "https://doi.org/10.5281/zenodo.18256663",
            "retrieved_at": timestamp_now(),
            "workflow_version": "battinfo-structure-refactor",
            "comment": (
                "Derived from parameters/h0b-base.json, parameters/equilibrium-calibration-parameters.json, and "
                "parameters/high-rate-calibration-parameters.json."
            ),
            "citation": "https://doi.org/10.5281/zenodo.18256663",
        },
        "comment": [
            "This JSON file is the canonical BattINFO-style descriptor for the calibrated IMP5-70-120-H0B cell.",
            "The JSON-LD companion preserves the legacy BattMo model-ontology links through dual typing on the corresponding measured-property nodes.",
        ],
    }


def build_jsonld(descriptor: dict[str, Any], to_jsonld_fn: Any) -> dict[str, Any]:
    jsonld_doc = deepcopy(to_jsonld_fn(descriptor, target="converter-compatible"))
    enrich_root_metadata(jsonld_doc, descriptor)
    attach_component_properties(jsonld_doc, descriptor)
    return jsonld_doc


def main() -> int:
    to_jsonld_fn, validate_json, _validate_jsonld = ensure_battinfo_runtime()

    descriptor = build_descriptor()
    validation = validate_json(descriptor, profile="cell-descriptor")
    if not validation.ok:
        raise ValueError(f"BattINFO JSON validation failed: {'; '.join(validation.errors)}")

    jsonld_doc = build_jsonld(descriptor, to_jsonld_fn)

    OUTPUT_JSON_PATH.write_text(json.dumps(descriptor, indent=2) + "\n", encoding="utf-8")
    OUTPUT_JSONLD_PATH.write_text(json.dumps(jsonld_doc, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
