#!/usr/bin/env python3

"""Read Motive's .mcal file and store a rich calibration snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, List

from optitrack_motive.mcal import parse_mcal
from optitrack_motive.presets import load_room


DEFAULT_MCAL_PATH = r"C:\ProgramData\OptiTrack\Motive\System Calibration.mcal"


def _timestamp_utc() -> str:
    return time.strftime("%y%m%d_%H%M", time.gmtime())


def _calib_root() -> Path:
    return Path(__file__).resolve().parents[1] / "optitrack_motive" / "calib"


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _hashable_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    stable = dict(payload)
    stable.pop("generated_at_utc", None)
    return stable


def _hash_payload(payload: Dict[str, Any]) -> str:
    serialized = json.dumps(
        _hashable_payload(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _looks_like_legacy_camera_name(name: Any) -> bool:
    return isinstance(name, str) and "#" in name


def _legacy_name_by_serial(calib_root: Path, room_prefix: str) -> Dict[int, str]:
    names: Dict[int, str] = {}
    for path in sorted(calib_root.glob(f"{room_prefix}*.json"), reverse=True):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue

        for camera in payload.get("cameras", []):
            if not isinstance(camera, dict):
                continue
            serial = camera.get("serial")
            name = camera.get("name")
            if not isinstance(serial, int) or not isinstance(name, str) or not name:
                continue
            if serial not in names or (_looks_like_legacy_camera_name(name) and not _looks_like_legacy_camera_name(names[serial])):
                names[serial] = name
    return names


def _legacy_cameras_from_mcal(parsed_cameras: List[Dict[str, Any]], previous_names: Dict[int, str]) -> List[Dict[str, Any]]:
    legacy_cameras: List[Dict[str, Any]] = []
    for camera in parsed_cameras:
        serial = camera.get("serial")
        name = previous_names.get(serial) if isinstance(serial, int) else None
        if not name:
            name = str(camera.get("name") or camera.get("serial_label") or "Camera")

        legacy_cameras.append(
            {
                "name": name,
                "serial": serial,
                "position": list(camera.get("position", [])),
                "orientation": list(camera.get("orientation", [])),
            }
        )
    return legacy_cameras


def _build_payload(
    parsed: Dict[str, Any],
    room: str,
    server_ip: str | None,
    client_ip: str | None,
    source_path: Path,
    previous_names: Dict[int, str],
) -> Dict[str, Any]:
    return {
        "format_version": 1,
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "server_ip": server_ip,
        "client_ip": client_ip,
        "room": room,
        "cameras": _legacy_cameras_from_mcal(parsed["cameras"], previous_names),
        "source_kind": "mcal",
        "source_path": str(source_path),
        "mcal": {
            "camera_count": parsed["camera_count"],
            "motive_build_info": parsed["motive_build_info"],
            "calibration_attributes": parsed["calibration_attributes"],
            "property_warehouse": parsed["property_warehouse"],
            "mask_data": parsed["mask_data"],
            "cameras": parsed["cameras"],
            "raw_mcal": parsed["raw_mcal"],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Store a rich camera calibration snapshot from a Motive .mcal file"
    )
    parser.add_argument("--mcal-path", default=DEFAULT_MCAL_PATH, help="Path to the Motive .mcal file")
    parser.add_argument("--room", default="cork", help="Room preset name (default: cork)")
    parser.add_argument("--server-ip", default="", help="Optional Motive server IP to record in the snapshot")
    args = parser.parse_args()

    mcal_path = Path(args.mcal_path)
    if not mcal_path.exists():
        raise FileNotFoundError(f".mcal file not found: {mcal_path}")

    print("Calib Import")
    print("=" * 40)
    print(f"Room      : {args.room or 'default'}")
    print(f"Source    : {mcal_path}")

    calib_root = _calib_root()
    calib_root.mkdir(parents=True, exist_ok=True)

    room_prefix = f"{args.room}_" if args.room else "calib_"
    snapshot_path = calib_root / f"{room_prefix}{_timestamp_utc()}.json"
    previous_names = _legacy_name_by_serial(calib_root, room_prefix)

    server_ip = args.server_ip or None
    client_ip = None
    if args.room:
        preset = load_room(args.room)
        if server_ip is None:
            server_ip = str(preset.connection.get("server_ip", "")) or None
        client_ip = str(preset.connection.get("client_ip", "")) or None

    parsed = parse_mcal(mcal_path)
    payload = _build_payload(parsed, args.room, server_ip, client_ip, mcal_path, previous_names)

    latest_existing = None
    for path in sorted(calib_root.glob(f"{room_prefix}*.json")):
        if path.name.endswith(".json") and path.name.startswith(room_prefix):
            latest_existing = path

    if latest_existing is not None:
        try:
            existing_payload = json.loads(latest_existing.read_text(encoding="utf-8"))
        except Exception:
            existing_payload = None

        if existing_payload is not None and _hash_payload(existing_payload) == _hash_payload(payload):
            print("No changes detected; latest calibration is identical.")
            print(f"Latest   : {latest_existing}")
            return

    _write_json(snapshot_path, payload)

    try:
        rel_snapshot = snapshot_path.relative_to(Path(__file__).resolve().parents[1])
    except ValueError:
        rel_snapshot = snapshot_path

    print(f"Saved {len(payload['cameras'])} cameras")
    print(f"Snapshot : {rel_snapshot}")
    print("Latest   : inferred from newest snapshot")


if __name__ == "__main__":
    main()
