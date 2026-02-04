#!/usr/bin/env python3

"""Load the latest calibration snapshot for a room."""

from __future__ import annotations

from optitrack_motive import calib


def main() -> None:
    room = "cork"
    calibs = calib.list_calibs(room=room)
    if not calibs:
        print(f"No calibration snapshots found for room '{room}'.")
        return

    latest_path = calibs[-1]
    data = calib.load_latest(room=room)
    if data is None:
        print(f"No calibration found for room '{room}'.")
        return

    cameras = data.get("cameras", [])
    print(f"Room        : {data.get('room', room)}")
    print(f"Generated   : {data.get('generated_at_utc')}")
    print(f"Server IP   : {data.get('server_ip')}")
    print(f"Camera count: {len(cameras)}")
    print(f"Latest file : {latest_path.name}")
    print()

    # Pick the most recent calibration at or before a target date.
    # Example: If you have calibs for Monday, Tuesday, Friday and ask for Thursday,
    # you will get Tuesday.
    target_date = "2026-02-05"
    prior_path = calib.find_calib_at_or_before(target_date, room=room)
    if prior_path is None:
        print(f"No calibration found at or before {target_date}.")
    else:
        print(f"Closest calib at/before {target_date}: {prior_path.name}")
    print()

    # Build a convenient dict keyed by camera name.
    by_name = {cam.get("name", f"camera_{i}"): cam for i, cam in enumerate(cameras)}

    # Print a compact summary for every camera.
    for name, cam in by_name.items():
        position = cam.get("position", ())
        orientation = cam.get("orientation", ())
        print(f"Camera: {name}")
        print(f"  Serial      : {cam.get('serial')}")
        print(f"  Position    : {position}")
        print(f"  Orientation : {orientation}")

        # Print any extra fields we might store in the future.
        extras = {
            key: value for key, value in cam.items()
            if key not in {"name", "serial", "position", "orientation"}
        }
        if extras:
            print(f"  Extras      : {extras}")
        print()


if __name__ == "__main__":
    main()
