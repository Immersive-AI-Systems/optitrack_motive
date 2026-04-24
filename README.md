# OptiTrack Motive

A modern Python client library for OptiTrack's NatNet streaming protocol, enabling real-time motion capture data retrieval from OptiTrack systems.

## Features

- 🚀 **Real-time streaming** - Receive motion capture data in real-time from OptiTrack systems
- 🎯 **Rigid body tracking** - Easy-to-use rigid body position and orientation tracking
- 📊 **Multiple data formats** - Support for labeled/unlabeled markers, skeletons, and assets
- 🔌 **Multiple protocols** - Built-in OSC and ZeroMQ integration examples
- 🛠️ **Diagnostic tools** - Frame drop detection and tracking diagnostics
- 📈 **Visualization** - Optional pygame-based real-time position visualization

## Installation

```bash
pip install git+https://github.com/Immersive-AI-Systems/optitrack_motive.git
```

### Dependencies
- Python 3.10+
- numpy
- Optional: pygame (for visualization), python-osc, zmq

## Quick Start

```python
from optitrack_motive.streaming.NatNetClient import NatNetClient

def receive_frame(data_dict):
    print(f"Frame {data_dict['frame_number']}: {len(data_dict['mocap_data'].rigid_body_data.rigid_body_list)} rigid bodies")

# Connect to OptiTrack server
client = NatNetClient()
client.set_server_address("10.40.49.47")  # Your OptiTrack server IP
client.new_frame_listener = receive_frame
client.run()
```

## Examples

### Basic Streaming

#### `hello_streaming_client.py`
Basic example showing how to connect and receive all motion capture data:
```bash
python examples/hello_streaming_client.py
```


### Native NatNet SampleClient
The tracked `examples/SampleClient` binary is refreshed from OptiTrack's official NatNet SDK 4.4.0 Ubuntu package and embeds `RUNPATH=$ORIGIN/../NatNet_SDK_4.4/lib`. On Tenerife, keep the SDK extracted at `~/git/optitrack_motive/NatNet_SDK_4.4` and run:
```bash
cd ~/git/optitrack_motive && ./examples/SampleClient 10.40.49.47
```

Official SDK source used for the refresh: `NatNet_SDK_4.4_ubuntu.tar`; the Windows ZIP has the same SampleClient/Python sources after CRLF normalization, plus extra Windows-only samples.

### Rigid Body Tracking

#### `print_rigid_body.py`
Track a specific rigid body in the terminal, or let the script auto-select the first visible rigid body:
```bash
# Auto-select the first visible rigid body
python examples/print_rigid_body.py -s 10.40.49.47

# Track rigid body "left"
python examples/print_rigid_body.py -n left -s 10.40.49.47 --max-frames 20

# Optional pygame visualization
python examples/print_rigid_body.py -n left -s 10.40.49.47 --pygame
```

#### `print_markers.py`
Print marker-set, labeled-marker, and unlabeled-marker positions:
```bash
# Print one frame of all marker positions
python examples/print_markers.py -s 10.40.49.47

# Print five marker frames
python examples/print_markers.py -s 10.40.49.47 --max-frames 5
```

### Protocol Integration

#### OSC (Open Sound Control)
Receive and send rigid body data via OSC:
```bash
# Receive OSC messages
python examples/osc_receive_rigid_body.py

# Send rigid body data as OSC messages
python scripts/osc_send_rigid_body.py
```

#### ZeroMQ
High-performance message queuing:
```bash
# Receive via ZeroMQ
python examples/zmq_receive_rigid_body.py

# Send via ZeroMQ
python scripts/zmq_send_rigid_body.py
```

## High-Level API

### MotiveReceiver
The main class for receiving motion capture data:

```python
from optitrack_motive.motive_receiver import MotiveReceiver

# Create receiver
motive = MotiveReceiver(server_ip="10.40.49.47")

# Get latest data
latest_frame = motive.get_last()
timestamp = motive.get_last_timestamp()

# Access rigid bodies by model name
rigid_body_data = motive.get_last_by_model("rigid_bodies_full", "MyRigidBody")

# Access marker data from the latest frame
rigid_body_names = motive.get_rigid_body_names()
marker_sets = motive.get_marker_sets()
labeled_markers = motive.get_labeled_markers()
unlabeled_markers = motive.get_unlabeled_markers()
```

### RigidBody
Simplified interface for tracking individual rigid bodies:

```python
from optitrack_motive.rigid_body import RigidBody
from optitrack_motive.motive_receiver import MotiveReceiver

motive = MotiveReceiver(server_ip="10.40.49.47")
rb = RigidBody(motive, "left")  # Track rigid body named "left"

# Get position and orientation
position = rb.get_position()  # [x, y, z]
rotation = rb.get_rotation()  # [qx, qy, qz, qw]
```

## Diagnostic Tools

### Frame Drop Detection
Monitor streaming performance and detect dropped frames:
```bash
python diagnostics/detect_frame_drops.py
```

### Rigid Body Tracker
Advanced rigid body tracking with detailed output:
```bash
python diagnostics/rigid_body_tracker.py
```

## Project Structure

```
optitrack_motive/
├── optitrack_motive/          # Main package
│   ├── streaming/             # Core NatNet streaming implementation
│   ├── motive_receiver.py     # High-level data receiver
│   └── rigid_body.py          # Rigid body tracking utilities
├── examples/                  # Usage examples
├── scripts/                   # Utility scripts for sending data
├── diagnostics/               # Diagnostic and debugging tools
└── logs/                      # Log files directory
```

## Configuration

### Server Connection
Configure your OptiTrack server connection:

```python
# Default localhost connection
client = NatNetClient()

# Custom server
client = NatNetClient()
client.set_server_address("192.168.1.100")
client.set_client_address("192.168.1.50")
client.set_use_multicast(True)
```

### Data Access
Access different types of motion capture data:

```python
def process_frame(data_dict):
    mocap_data = data_dict["mocap_data"]
    
    # Rigid bodies
    rigid_bodies = mocap_data.rigid_body_data.rigid_body_list
    
    # Labeled markers
    labeled_markers = mocap_data.labeled_marker_data.labeled_marker_list
    
    # Unlabeled markers  
    unlabeled_markers = mocap_data.legacy_other_markers
    
    # Skeletons
    skeletons = mocap_data.skeleton_data.skeleton_list
```

## Calibration
Fetch and store camera calibration snapshots from Motive:

```bash
python scripts/update_calib.py
```

Or ingest the full Motive `.mcal` calibration file:

```bash
python scripts/update_calib_from_mcal.py --mcal-path "C:\ProgramData\OptiTrack\Motive\System Calibration.mcal"
```

Windows runner (conda env + pull + update + conditional commit/push):

```powershell
powershell -ExecutionPolicy Bypass -File scripts/update_calib_windows.ps1 -CondaEnv rtd
```

Desktop/shortcut-friendly wrapper that keeps the window open on failure:

```cmd
scripts\run_update_calib_windows.cmd -CondaEnv rtd
```

When you use the default live Motive `.mcal` path, Motive must already be running.
The wrapper leaves the shell open and the runner prints a clear error if Motive is not open.

From another machine via SSH to `Admin@kyushu`:

```bash
ssh Admin@kyushu 'powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\Admin\git\optitrack_motive\scripts\update_calib_windows.ps1" -CondaEnv rtd'
```

The Windows runner now defaults to the richer local `.mcal` source at
`C:\ProgramData\OptiTrack\Motive\System Calibration.mcal`. Use
`-CalibrationSource natnet` if you want the older NatNet-only fetch path.

Defaults to room `cork`. Snapshots are saved as:

`optitrack_motive/calib/<room>_YYMMDD_HHMM.json`

The latest calibration is inferred from the newest snapshot. If the calibration payload is
identical to the previous snapshot, the script skips saving and reports no changes.

Load and query calibrations:

```python
from optitrack_motive import calib

# Latest calibration for a room
latest = calib.load_latest(room="cork")

# List all calibration files
all_calibs = calib.list_calibs(room="cork")

# Find the closest calibration at or before a date
closest = calib.find_calib_at_or_before("2026-02-05", room="cork")

# Build a dict keyed by camera name
by_name = {cam["name"]: cam for cam in latest.get("cameras", [])}
first = next(iter(by_name.values()), None)
if first:
    print(first["serial"], first["position"], first["orientation"])
```

When the `.mcal` path is used, the top-level `cameras` list keeps the old compact schema
(`name`, `serial`, `position`, `orientation`) for compatibility. The richer `.mcal`
content is stored separately under `latest["mcal"]`, including camera properties,
attributes, intrinsics, extrinsics, filter settings, mask data, and the full `raw_mcal`
tree for fields not yet normalized.

## Recording and Playback

Record streaming data for later analysis:
```python
motive = MotiveReceiver(
    server_ip="10.40.49.47",
    do_record_streaming=True,
    fn_mock="my_recording.pkl"
)
```

Playback recorded data:
```python
motive = MotiveReceiver(
    server_ip="10.40.49.47", 
    do_mock_streaming=True,
    fn_mock="my_recording.pkl"
)
```

## License

Apache License 2.0 - see LICENSE file for details.

## Contributing

Contributions welcome! Please feel free to submit issues and pull requests.
