from __future__ import annotations

from pathlib import Path
from typing import Any
import re
import xml.etree.ElementTree as ET


def convert_to_number(value: Any) -> Any:
    """Convert XML string values to int/float when possible."""
    try:
        if value is None:
            return value

        value = str(value).strip()

        if value == "":
            return value

        if "." in value:
            return float(value)

        return int(value)

    except (ValueError, TypeError):
        return value


def parse_datetime_from_filename(filename: str) -> tuple[str, str]:
    """
    Extract YYYYMMDD and HHMMSS from filename.

    Expected pattern:
        something_YYYYMMDD_HHMMSS.xml
    """
    match = re.search(r"(\d{8})_(\d{6})", filename)

    if match:
        date_str, time_str = match.groups()
        return date_str, time_str

    return "unknown_date", "unknown_time"


def parse_nivus_xml(xml_path: str | Path) -> dict[str, list[dict[str, Any]]]:
    """
    Parse Nivus XML into raw groups:
    Summary, Sections, Points, Gates.
    """

    xml_path = Path(xml_path)

    tree = ET.parse(xml_path)
    root = tree.getroot()

    data: dict[str, list[dict[str, Any]]] = {
        "Summary": [],
        "Sections": [],
        "Points": [],
        "Gates": [],
    }

    timestamp = root.find("./timestamp")

    if timestamp is None:
        raise ValueError(f"Nivus XML mismatch: missing ./timestamp in {xml_path}")

    # Summary
    for element in timestamp:
        if element.tag not in ["sect", "point"]:
            unit = element.attrib.get("unit", "")
            parameter = f"{element.tag} [{unit}]" if unit else element.tag
            value = element.attrib.get("val", "")
            data["Summary"].append(
                {
                    "Parameter": parameter,
                    "Value": convert_to_number(value),
                }
            )

    # Sections
    for sect in root.findall("./timestamp/sect"):
        section_data = {
            attr: convert_to_number(sect.attrib.get(attr, ""))
            for attr in sect.attrib
        }

        for child in sect:
            unit = child.attrib.get("unit", "")
            key = f"{child.tag} [{unit}]" if unit else child.tag
            section_data[key] = convert_to_number(child.attrib.get("val", ""))

        data["Sections"].append(section_data)

    # Points
    for point in root.findall("./timestamp/point"):
        point_data = {
            attr: convert_to_number(point.attrib.get(attr, ""))
            for attr in point.attrib
        }

        for child in point:
            if child.tag == "gate":
                continue

            unit = child.attrib.get("unit", "")
            key = f"{child.tag} [{unit}]" if unit else child.tag
            point_data[key] = convert_to_number(child.attrib.get("val", ""))

        data["Points"].append(point_data)

    # Gates
    for point in root.findall("./timestamp/point"):
        point_index = point.attrib.get("index", "")

        for gate in point.findall("./gate"):
            gate_data = {
                attr: convert_to_number(gate.attrib.get(attr, ""))
                for attr in gate.attrib
            }

            for child in gate:
                unit = child.attrib.get("unit", "")
                key = f"{child.tag} [{unit}]" if unit else child.tag
                gate_data[key] = convert_to_number(child.attrib.get("val", ""))

            gate_data["Point Index"] = convert_to_number(point_index)
            data["Gates"].append(gate_data)

    return data