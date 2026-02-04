"""Access calibration data stored in this package."""

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path
from typing import Any, Dict, List, Optional


def _calib_root() -> Path:
    return resources.files(__package__)  # type: ignore[return-value]


def _latest_filename(room: Optional[str]) -> str:
    if room:
        return f"{room}_latest.json"
    return "calib_latest.json"


def latest_json_path(room: Optional[str] = None) -> Optional[Path]:
    """Return the latest calibration JSON path if it exists."""
    snapshots = list_snapshots(room)
    if snapshots:
        return snapshots[-1]

    # Backward compatibility with previous layout.
    root = _calib_root()
    legacy_dir = root / "latest"
    legacy_name = f"{room}_calib.json" if room else "calib.json"
    legacy_path = legacy_dir / legacy_name
    if legacy_path.exists():
        return legacy_path

    legacy_latest = root / _latest_filename(room)
    return legacy_latest if legacy_latest.exists() else None


def load_latest(room: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Load the latest calibration JSON if available."""
    path = latest_json_path(room)
    if path is None:
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_snapshots(room: Optional[str] = None) -> List[Path]:
    """Return sorted snapshot files (newest last)."""
    root = _calib_root()
    if not root.exists():
        return []

    prefix = f"{room}_" if room else "calib_"
    snapshots = [
        p for p in root.iterdir()
        if p.is_file() and p.name.startswith(prefix) and p.name.endswith(".json")
        and "latest" not in p.name
    ]
    return sorted(snapshots, key=lambda p: p.name)
