from __future__ import annotations

import unittest
from unittest.mock import patch

from optitrack_motive.motive_stream import fetch_camera_statuses


class FetchCameraStatusesTests(unittest.TestCase):
    def test_fetch_camera_statuses_returns_dict_keyed_by_camera_name(self) -> None:
        cameras = [
            {
                "name": "PrimeX 22 #103517",
                "serial": 103517,
                "position": (1.0, 2.0, 3.0),
                "orientation": (0.0, 0.0, 0.0, 1.0),
            }
        ]
        property_values = {
            ("PrimeX 22 #103517", "Video Mode"): "11",
            ("PrimeX 22 #103517", "Enabled"): "true",
            ("PrimeX 22 #103517", "Reconstruction"): "false",
        }

        fake_socket = object()

        with patch(
            "optitrack_motive.motive_stream.fetch_camera_descriptions",
            return_value=(cameras, "10.0.0.5"),
        ), patch(
            "optitrack_motive.motive_stream._open_natnet_command_socket"
        ) as open_socket, patch(
            "optitrack_motive.motive_stream._request_motive_text"
        ) as request_text:
            open_socket.return_value.__enter__.return_value = fake_socket
            open_socket.return_value.__exit__.return_value = False

            def side_effect(sock: object, server_ip: str, command: str) -> str:
                self.assertIs(sock, fake_socket)
                self.assertEqual(server_ip, "10.0.0.1")
                _, name, prop = command.split(",", 2)
                return property_values[(name, prop)]

            request_text.side_effect = side_effect

            status = fetch_camera_statuses("10.0.0.1")

        self.assertEqual(status["server_ip"], "10.0.0.1")
        self.assertEqual(status["client_ip"], "10.0.0.5")
        self.assertEqual(status["camera_count"], 1)

        camera = status["cameras"]["PrimeX 22 #103517"]
        self.assertEqual(camera["serial"], 103517)
        self.assertEqual(camera["video_mode"], 11)
        self.assertEqual(camera["video_mode_name"], "Duplex")
        self.assertTrue(camera["enabled"])
        self.assertFalse(camera["reconstruction_enabled"])
        self.assertTrue(camera["duplex"])


if __name__ == "__main__":
    unittest.main()
