from __future__ import annotations

from pathlib import Path
from typing import Any
import re
import xml.etree.ElementTree as ET


def convert_to_number(value: Any) -> Any:
    """Convert XML string values to int/float when possible."""
    if value is None:
        return ""

    value = str(value).strip()

    if value == "":
        return ""

    try:
        # Accept decimal values and scientific notation.
        if any(ch in value.lower() for ch in [".", "e"]):
            return float(value)
        return int(value)
    except (ValueError, TypeError):
        return value


def parse_datetime_from_filename(filename: str) -> tuple[str, str]:
    """
    Extract YYYYMMDD and HHMMSS from filename.

    Expected pattern examples:
        20251215_P8_Chamizo_R3_20251215_124600.xml
        something_20251215_124600.xml
    """
    matches = re.findall(r"(\d{8})_(\d{6})", filename)

    if matches:
        # Use the last match because Nivus filenames may contain a date twice.
        date_str, time_str = matches[-1]
        return date_str, time_str

    return "unknown_date", "unknown_time"


def _key_from_element(element: ET.Element) -> str:
    """Build a clean column name from XML tag and unit attribute."""
    unit = element.attrib.get("unit", "").strip()
    return f"{element.tag} [{unit}]" if unit else element.tag


def _value_from_element(element: ET.Element) -> Any:
    """Read the main value of a Nivus XML element."""
    if "val" in element.attrib:
        return convert_to_number(element.attrib.get("val"))

    text = (element.text or "").strip()
    return convert_to_number(text) if text else ""


def _simple_children_to_row(parent: ET.Element, skip_tags: set[str] | None = None) -> dict[str, Any]:
    """
    Convert direct children with val/unit attributes into columns.

    Nested complex children can be skipped, e.g. point/gate or timestamp/sect.
    """
    skip_tags = skip_tags or set()
    row: dict[str, Any] = {}

    for child in parent:
        if child.tag in skip_tags:
            continue

        # Skip complex containers without val/text. Example: empty <calib>.
        has_children = len(list(child)) > 0
        has_value = "val" in child.attrib or (child.text or "").strip()

        if has_children and not has_value:
            continue

        row[_key_from_element(child)] = _value_from_element(child)

    return row


def parse_nivus_xml(xml_path: str | Path) -> dict[str, list[dict[str, Any]]]:
    """
    Parse a Nivus XML file into clean raw tabular groups.

    Returns four groups:
        Summary  -> one horizontal row per XML file
        Sections -> one row per <sect>
        Points   -> one row per <point>
        Gates    -> one row per <gate>, including parent point_index

    This function intentionally does NOT normalize column names into an Aforix
    canonical schema. It preserves the raw Nivus variable names and units, e.g.
    'q [l/s]', 'h [m]', 'v [m/s]'.
    """
    xml_path = Path(xml_path)

    tree = ET.parse(xml_path)
    root = tree.getroot()
    timestamp = root.find("./timestamp")

    if timestamp is None:
        raise ValueError(f"Nivus XML mismatch: missing ./timestamp in {xml_path}")

    data: dict[str, list[dict[str, Any]]] = {
        "Summary": [],
        "Sections": [],
        "Points": [],
        "Gates": [],
    }

    # ---------- Summary: one horizontal row ----------
    summary: dict[str, Any] = {}

    # Archive-level metadata.
    for attr, value in root.attrib.items():
        summary[f"archive_{attr}"] = convert_to_number(value)

    # Timestamp-level metadata.
    for attr, value in timestamp.attrib.items():
        summary[f"timestamp_{attr}"] = convert_to_number(value)

    # Direct timestamp children, excluding tabular groups.
    summary.update(_simple_children_to_row(timestamp, skip_tags={"sect", "point", "calib"}))

    data["Summary"].append(summary)

    # ---------- Sections: one row per <sect> ----------
    for sect in timestamp.findall("./sect"):
        row: dict[str, Any] = {}

        for attr, value in sect.attrib.items():
            row[attr] = convert_to_number(value)

        row.update(_simple_children_to_row(sect))
        data["Sections"].append(row)

    # ---------- Points: one row per <point>, excluding nested gates ----------
    for point in timestamp.findall("./point"):
        row: dict[str, Any] = {}

        for attr, value in point.attrib.items():
            row[attr] = convert_to_number(value)

        row.update(_simple_children_to_row(point, skip_tags={"gate"}))
        data["Points"].append(row)

    # ---------- Gates: one row per <gate>, preserving parent point index ----------
    for point in timestamp.findall("./point"):
        point_index = convert_to_number(point.attrib.get("index", ""))

        for gate in point.findall("./gate"):
            row: dict[str, Any] = {"point_index": point_index}

            for attr, value in gate.attrib.items():
                row[attr] = convert_to_number(value)

            row.update(_simple_children_to_row(gate))
            data["Gates"].append(row)

    return data
