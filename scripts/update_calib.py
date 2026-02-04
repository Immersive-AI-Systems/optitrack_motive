#!/usr/bin/env python3

"""Fetch camera descriptions from Motive and store them in this repo."""

from __future__ import annotations

import argparse
import json
import hashlib
import time
from pathlib import Path
from typing import Any, Dict, List

from optitrack_motive.motive_stream import fetch_camera_descriptions
from optitrack_motive.presets import load_room


DEFAULT_SERVER_IP = "10.40.49.47"
DEFAULT_TIMEOUT = 8.0


def _timestamp_utc() -> str:
    return time.strftime("%y%m%d_%H%M", time.gmtime())


def _calib_root() -> Path:
    return Path(__file__).resolve().parents[1] / "optitrack_motive" / "calib"


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _hash_payload(payload: Dict[str, Any]) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch camera descriptions from Motive and store them under optitrack_motive/calib"
    )
    parser.add_argument("--server-ip", default=DEFAULT_SERVER_IP, help="Motive server IP address")
    parser.add_argument("--client-ip", default="auto", help="Client IP (default: auto detect)")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="Seconds to wait for data descriptions")
    parser.add_argument("--no-multicast", action="store_true", help="Use unicast instead of multicast")
    parser.add_argument("--room", default="cork", help="Room preset name (default: cork)")
    args = parser.parse_args()

    room_name = args.room
    server_ip = args.server_ip
    client_ip = args.client_ip
    use_multicast = not args.no_multicast

    if room_name:
        preset = load_room(room_name)
        server_ip = str(preset.connection.get("server_ip", server_ip))
        client_ip = str(preset.connection.get("client_ip", client_ip))
        if not args.no_multicast:
            use_multicast = bool(preset.connection.get("use_multicast", use_multicast))

    label_room = room_name or "default"
    print("Calib Fetch")
    print("=" * 40)
    print(f"Room      : {label_room}")
    print(f"Server IP : {server_ip}")
    print(f"Client IP : {client_ip}")
    print(f"Multicast : {use_multicast}")

    cameras_raw, resolved_client_ip = fetch_camera_descriptions(
        server_ip,
        client_ip,
        args.timeout,
        verbose=False,
        use_multicast=use_multicast,
    )
    print(f"Resolved Client IP : {resolved_client_ip}")

    timestamp = _timestamp_utc()
    payload: Dict[str, Any] = {
        "format_version": 1,
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "server_ip": server_ip,
        "client_ip": resolved_client_ip,
        "room": room_name,
        "cameras": cameras_raw,
    }

    calib_root = _calib_root()
    calib_root.mkdir(parents=True, exist_ok=True)

    room_prefix = f"{room_name}_" if room_name else "calib_"
    snapshot_path = calib_root / f"{room_prefix}{timestamp}.json"

    latest_existing = None
    for path in sorted(calib_root.glob(f"{room_prefix}*.json")):
        if path.name.endswith(".json") and path.name.startswith(room_prefix):
            latest_existing = path

    if latest_existing is not None:
        try:
            existing_payload = json.loads(latest_existing.read_text(encoding="utf-8"))
        except Exception:
            existing_payload = None

        if existing_payload is not None:
            if _hash_payload(existing_payload) == _hash_payload(payload):
                print("No changes detected; latest calibration is identical.")
                print(f"Latest   : {latest_existing}")
                return

    _write_json(snapshot_path, payload)

    try:
        rel_snapshot = snapshot_path.relative_to(Path(__file__).resolve().parents[1])
    except ValueError:
        rel_snapshot = snapshot_path
    print(f"Saved {len(cameras_raw)} cameras")
    print(f"Snapshot : {rel_snapshot}")
    print("Latest   : inferred from newest snapshot")


if __name__ == "__main__":
    main()
