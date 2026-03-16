"""Helpers for reading Motive .mcal calibration exports."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Union


PathLike = Union[str, Path]


def _float_attr(attrs: Dict[str, str], key: str, default: float = 0.0) -> float:
    value = attrs.get(key)
    if value is None:
        return default
    return float(value)


def _matrix_to_quaternion(values: Iterable[float]) -> List[float]:
    """Convert a row-major 3x3 rotation matrix into a quaternion."""
    m = list(values)
    if len(m) != 9:
        raise ValueError("Rotation matrix must contain exactly 9 values.")

    m00, m01, m02 = m[0], m[1], m[2]
    m10, m11, m12 = m[3], m[4], m[5]
    m20, m21, m22 = m[6], m[7], m[8]

    trace = m00 + m11 + m22
    if trace > 0.0:
        s = (trace + 1.0) ** 0.5 * 2.0
        w = 0.25 * s
        x = (m21 - m12) / s
        y = (m02 - m20) / s
        z = (m10 - m01) / s
    elif m00 > m11 and m00 > m22:
        s = (1.0 + m00 - m11 - m22) ** 0.5 * 2.0
        w = (m21 - m12) / s
        x = 0.25 * s
        y = (m01 + m10) / s
        z = (m02 + m20) / s
    elif m11 > m22:
        s = (1.0 + m11 - m00 - m22) ** 0.5 * 2.0
        w = (m02 - m20) / s
        x = (m01 + m10) / s
        y = 0.25 * s
        z = (m12 + m21) / s
    else:
        s = (1.0 + m22 - m00 - m11) ** 0.5 * 2.0
        w = (m10 - m01) / s
        x = (m02 + m20) / s
        y = (m12 + m21) / s
        z = 0.25 * s

    return [float(x), float(y), float(z), float(w)]


def _element_to_tree(element: ET.Element) -> Dict[str, Any]:
    """Convert XML into a JSON-friendly tree while preserving all attributes."""
    node: Dict[str, Any] = {}
    if element.attrib:
        node["attributes"] = dict(element.attrib)

    text = (element.text or "").strip()
    children = [child for child in list(element) if isinstance(child.tag, str)]
    if text:
        node["text"] = text

    if not children:
        return node

    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for child in children:
        grouped[child.tag].append(_element_to_tree(child))

    for tag, items in grouped.items():
        node[tag] = items[0] if len(items) == 1 else items
    return node


def _parse_camera(camera: ET.Element) -> Dict[str, Any]:
    serial_label = camera.attrib.get("Serial", "")
    serial_match = re.search(r"(\d+)$", serial_label)
    serial_number = int(serial_match.group(1)) if serial_match else None

    sections = {child.tag: child for child in camera if isinstance(child.tag, str)}
    properties = dict(sections["Properties"].attrib) if "Properties" in sections else {}
    attributes = dict(sections["Attributes"].attrib) if "Attributes" in sections else {}
    intrinsic = dict(sections["Intrinsic"].attrib) if "Intrinsic" in sections else {}
    intrinsic_standard = (
        dict(sections["IntrinsicStandardCameraModel"].attrib)
        if "IntrinsicStandardCameraModel" in sections
        else {}
    )
    extrinsic = dict(sections["Extrinsic"].attrib) if "Extrinsic" in sections else {}
    software_filters = (
        dict(sections["CameraSoftwareFilters"].attrib)
        if "CameraSoftwareFilters" in sections
        else {}
    )
    hardware_filters = (
        dict(sections["CameraHardwareFilters"].attrib)
        if "CameraHardwareFilters" in sections
        else {}
    )
    calibration = dict(sections["Calibration"].attrib) if "Calibration" in sections else {}
    color_camera = dict(sections["ColorCamera"].attrib) if "ColorCamera" in sections else {}

    position = [
        _float_attr(extrinsic, "X"),
        _float_attr(extrinsic, "Y"),
        _float_attr(extrinsic, "Z"),
    ]
    orientation_matrix = [
        _float_attr(extrinsic, f"OrientMatrix{i}")
        for i in range(9)
        if f"OrientMatrix{i}" in extrinsic
    ]
    orientation = _matrix_to_quaternion(orientation_matrix) if len(orientation_matrix) == 9 else []

    return {
        "name": serial_label or f"Camera {properties.get('CameraID', '')}".strip(),
        "serial": serial_number,
        "serial_label": serial_label,
        "position": position,
        "orientation": orientation,
        "orientation_matrix": orientation_matrix,
        "properties": properties,
        "attributes": attributes,
        "intrinsic": intrinsic,
        "intrinsic_standard_camera_model": intrinsic_standard,
        "extrinsic": extrinsic,
        "camera_software_filters": software_filters,
        "camera_hardware_filters": hardware_filters,
        "calibration": calibration,
        "color_camera": color_camera or None,
    }


def parse_mcal(path: PathLike) -> Dict[str, Any]:
    """Parse a Motive .mcal file into a rich JSON-friendly dict."""
    path = Path(path)
    root = ET.fromstring(path.read_text(encoding="utf-16"))

    calibration = root.find("Calibration")
    if calibration is None:
        raise ValueError(f"No Calibration node found in {path}")

    cameras_elem = calibration.find("Cameras")
    cameras = []
    if cameras_elem is not None:
        cameras = [
            _parse_camera(camera)
            for camera in cameras_elem
            if isinstance(camera.tag, str) and camera.tag == "Camera"
        ]

    calibration_attributes_elem = calibration.find("CalibrationAttributes")
    property_warehouse_elem = root.find("property_warehouse")
    mask_data_elem = root.find("MaskData")
    motive_build_info_elem = root.find("MotiveBuildInfo")

    return {
        "motive_build_info": dict(motive_build_info_elem.attrib) if motive_build_info_elem is not None else {},
        "camera_count": len(cameras),
        "cameras": cameras,
        "calibration_attributes": (
            _element_to_tree(calibration_attributes_elem) if calibration_attributes_elem is not None else {}
        ),
        "property_warehouse": (
            _element_to_tree(property_warehouse_elem) if property_warehouse_elem is not None else {}
        ),
        "mask_data": _element_to_tree(mask_data_elem) if mask_data_elem is not None else {},
        "raw_mcal": {
            "tag": root.tag,
            "attributes": dict(root.attrib),
            "children": _element_to_tree(root),
        },
    }
