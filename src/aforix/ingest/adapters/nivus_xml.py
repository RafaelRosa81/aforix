from __future__ import annotations

from pathlib import Path
from typing import Any
import datetime as dt
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
        if any(ch in value.lower() for ch in [".", "e"]):
            return float(value)
        return int(value)
    except (ValueError, TypeError):
        return value


def parse_datetime_from_timestamp(value: Any) -> tuple[str, str]:
    """
    Extract YYYYMMDD and HHMMSS from Nivus timestamp time value.

    Expected example:
        2025-06-25T10:14:46
    """

    text = str(value or "").strip()

    if not text:
        return "unknown_date", "unknown_time"

    for fmt in (
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
    ):
        try:
            parsed = dt.datetime.strptime(text, fmt)
            return parsed.strftime("%Y%m%d"), parsed.strftime("%H%M%S")
        except ValueError:
            continue

    match = re.search(
        r"(?P<date>\d{4})[-/](?P<month>\d{2})[-/](?P<day>\d{2})[T\s_]"
        r"(?P<hour>\d{2}):?(?P<minute>\d{2}):?(?P<second>\d{2})",
        text,
    )

    if match:
        return (
            f"{match.group('date')}{match.group('month')}{match.group('day')}",
            f"{match.group('hour')}{match.group('minute')}{match.group('second')}",
        )

    return "unknown_date", "unknown_time"


def parse_datetime_from_filename(filename: str) -> tuple[str, str]:
    """
    Fallback: extract YYYYMMDD and HHMMSS from filename.
    """

    matches = re.findall(r"(\d{8})_(\d{6})", filename)

    if matches:
        date_str, time_str = matches[-1]
        return date_str, time_str

    return "unknown_date", "unknown_time"


def parse_nivus_metadata(xml_path: str | Path) -> dict[str, Any]:
    """
    Extract core metadata from a Nivus XML file.

    Main source:
        station_id   -> <ref val="...">
        station_name -> <name val="...">
        datetime     -> <timestamp time="...">
    """

    xml_path = Path(xml_path)

    tree = ET.parse(xml_path)
    root = tree.getroot()
    timestamp = root.find("./timestamp")

    if timestamp is None:
        raise ValueError(f"Nivus XML mismatch: missing ./timestamp in {xml_path}")

    timestamp_time = timestamp.attrib.get("time", "")
    measurement_date, measurement_time = parse_datetime_from_timestamp(timestamp_time)

    station_id = ""
    station_name = ""

    ref = timestamp.find("./ref")
    if ref is not None:
        station_id = str(ref.attrib.get("val", "")).strip()

    name = timestamp.find("./name")
    if name is not None:
        station_name = str(name.attrib.get("val", "")).strip()

    return {
        "station_id": station_id,
        "station_name": station_name,
        "timestamp_time": timestamp_time,
        "measurement_date": measurement_date,
        "measurement_time": measurement_time,
        "input_file": xml_path.name,
        "input_path": str(xml_path.resolve()),
    }


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


def _simple_children_to_row(
    parent: ET.Element,
    skip_tags: set[str] | None = None,
) -> dict[str, Any]:
    """
    Convert direct children with val/unit attributes into columns.
    """

    skip_tags = skip_tags or set()
    row: dict[str, Any] = {}

    for child in parent:
        if child.tag in skip_tags:
            continue

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

    summary: dict[str, Any] = {}

    for attr, value in root.attrib.items():
        summary[f"archive_{attr}"] = convert_to_number(value)

    for attr, value in timestamp.attrib.items():
        summary[f"timestamp_{attr}"] = convert_to_number(value)

    summary.update(
        _simple_children_to_row(
            timestamp,
            skip_tags={"sect", "point", "calib"},
        )
    )

    data["Summary"].append(summary)

    for sect in timestamp.findall("./sect"):
        row: dict[str, Any] = {}

        for attr, value in sect.attrib.items():
            row[attr] = convert_to_number(value)

        row.update(_simple_children_to_row(sect))
        data["Sections"].append(row)

    for point in timestamp.findall("./point"):
        row: dict[str, Any] = {}

        for attr, value in point.attrib.items():
            row[attr] = convert_to_number(value)

        row.update(_simple_children_to_row(point, skip_tags={"gate"}))
        data["Points"].append(row)

    for point in timestamp.findall("./point"):
        point_index = convert_to_number(point.attrib.get("index", ""))

        for gate in point.findall("./gate"):
            row: dict[str, Any] = {"point_index": point_index}

            for attr, value in gate.attrib.items():
                row[attr] = convert_to_number(value)

            row.update(_simple_children_to_row(gate))
            data["Gates"].append(row)

    return data