from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "update_calib_from_mcal.py"
SPEC = importlib.util.spec_from_file_location("update_calib_from_mcal", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


SAMPLE_PARSED = {
    "camera_count": 1,
    "motive_build_info": {"AppVersion": "3.4.0.2"},
    "calibration_attributes": {"TriangulationMeanResidual": {"attributes": {"Error": "0.001"}}},
    "property_warehouse": {"properties": {"property": {"attributes": {"name": "PCResidual"}}}},
    "mask_data": {},
    "cameras": [
        {
            "name": "M103517",
            "serial": 103517,
            "serial_label": "M103517",
            "position": [1.0, 2.0, 3.0],
            "orientation": [0.0, 0.0, 0.0, 1.0],
            "orientation_matrix": [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0],
            "properties": {"CameraID": "6"},
            "attributes": {"Revision": "50"},
            "intrinsic": {"k1": "0.1"},
            "intrinsic_standard_camera_model": {"k1": "0.01"},
            "extrinsic": {"X": "1.0", "Y": "2.0", "Z": "3.0"},
            "camera_software_filters": {"FilterLevel": "2"},
            "camera_hardware_filters": {"GrayscaleFloor": "48"},
            "calibration": {"PartitionID": "1"},
            "color_camera": None,
        }
    ],
    "raw_mcal": {"tag": "calibrationProfile", "attributes": {"version": "1"}, "children": {}},
}


class UpdateCalibFromMcalTests(unittest.TestCase):
    def test_legacy_name_by_serial_prefers_old_camera_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "cork_260316_1328.json").write_text(
                json.dumps(
                    {
                        "cameras": [
                            {
                                "name": "M103517",
                                "serial": 103517,
                                "position": [1.0, 2.0, 3.0],
                                "orientation": [0.0, 0.0, 0.0, 1.0],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (root / "cork_260316_1234.json").write_text(
                json.dumps(
                    {
                        "cameras": [
                            {
                                "name": "PrimeX 22 #103517",
                                "serial": 103517,
                                "position": [1.0, 2.0, 3.0],
                                "orientation": [0.0, 0.0, 0.0, 1.0],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            names = MODULE._legacy_name_by_serial(root, "cork_")

        self.assertEqual(names[103517], "PrimeX 22 #103517")

    def test_build_payload_keeps_legacy_camera_shape_and_nests_mcal(self) -> None:
        payload = MODULE._build_payload(
            SAMPLE_PARSED,
            room="cork",
            server_ip="10.40.49.47",
            client_ip="auto",
            source_path=Path(r"C:\ProgramData\OptiTrack\Motive\System Calibration.mcal"),
            previous_names={103517: "PrimeX 22 #103517"},
        )

        self.assertEqual(payload["format_version"], 1)
        self.assertEqual(payload["server_ip"], "10.40.49.47")
        self.assertEqual(payload["client_ip"], "auto")
        self.assertEqual(
            sorted(payload["cameras"][0].keys()),
            ["name", "orientation", "position", "serial"],
        )
        self.assertEqual(payload["cameras"][0]["name"], "PrimeX 22 #103517")
        self.assertNotIn("attributes", payload["cameras"][0])
        self.assertIn("mcal", payload)
        self.assertEqual(payload["mcal"]["camera_count"], 1)
        self.assertEqual(payload["mcal"]["cameras"][0]["attributes"]["Revision"], "50")


if __name__ == "__main__":
    unittest.main()
