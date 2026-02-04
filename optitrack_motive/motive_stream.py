"""Helpers for retrieving OptiTrack data via the NatNet client."""

from __future__ import annotations

import socket
import re
import threading
import time
from typing import Any, Dict, List, Tuple

from .streaming.NatNetClient import NatNetClient


def resolve_client_ip(server_ip: str, requested: str = "auto") -> str:
    """Determine the appropriate client IP for NatNet streaming."""
    if requested and requested.lower() not in {"", "auto"}:
        return requested

    if server_ip.startswith("127.") or server_ip.lower() == "localhost":
        return "127.0.0.1"

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect((server_ip, 1511))
            return sock.getsockname()[0]
    except OSError:
        # Fall back to binding all interfaces if detection fails.
        return "0.0.0.0"


def _parse_camera_descriptions(data_descs: Any) -> List[Dict[str, Any]]:
    """Extract camera metadata from a NatNet model definition."""
    cameras: List[Dict[str, Any]] = []
    for camera_desc in getattr(data_descs, "camera_list", []):
        name = getattr(camera_desc, "name", getattr(camera_desc, "camera_name", "Camera"))
        if isinstance(name, bytes):
            name = name.decode("utf-8", errors="ignore")
        name_str = str(name)
        serial = None
        match = re.search(r"#\s*(\d+)", name_str)
        if match:
            serial = int(match.group(1))

        raw_position = list(getattr(camera_desc, "position", [0.0, 0.0, 0.0]))
        if len(raw_position) < 3:
            raw_position = (raw_position + [0.0, 0.0, 0.0])[:3]

        raw_orientation = list(getattr(camera_desc, "orientation", [0.0, 0.0, 0.0, 1.0]))
        if len(raw_orientation) < 4:
            raw_orientation = (raw_orientation + [0.0, 0.0, 0.0, 1.0])[:4]

        position = tuple(float(x) for x in raw_position[:3])
        orientation = tuple(float(x) for x in raw_orientation[:4])

        cameras.append({
            "name": name_str,
            "serial": serial,
            "position": position,
            "orientation": orientation,
        })

    return cameras


def fetch_camera_descriptions(
    server_ip: str,
    client_ip: str = "auto",
    timeout: float = 8.0,
    verbose: bool = False,
    use_multicast: bool = True,
) -> Tuple[List[Dict[str, Any]], str]:
    """Retrieve camera descriptions from Motive via NatNet."""
    resolved_client_ip = resolve_client_ip(server_ip, client_ip)

    client = NatNetClient()
    client.set_server_address(server_ip)
    client.set_client_address(resolved_client_ip)
    client.set_use_multicast(use_multicast)

    if hasattr(client, "set_print_level"):
        client.set_print_level(1 if verbose else 0)
    if hasattr(client, "set_suppress_output"):
        client.set_suppress_output(not verbose)

    data_descs_holder: Dict[str, Any] = {}
    data_descs_event = threading.Event()

    def on_data_descs(data_descs: Any) -> None:
        data_descs_holder["data"] = data_descs
        data_descs_event.set()

    client.data_description_listener = on_data_descs

    if not client.run('c'):
        client.data_description_listener = None
        raise RuntimeError("Failed to start NatNet client")

    try:
        client.send_request(
            client.command_socket,
            client.NAT_REQUEST_MODELDEF,
            "",
            (client.server_ip_address, client.command_port),
        )

        deadline = time.time() + timeout
        while time.time() < deadline:
            if data_descs_event.wait(timeout=0.1):
                data_descs = data_descs_holder.get("data")
                cameras = _parse_camera_descriptions(data_descs)
                return cameras, resolved_client_ip

        raise TimeoutError("Timed out waiting for camera descriptions from Motive")
    finally:
        client.data_description_listener = None
        client.shutdown()
