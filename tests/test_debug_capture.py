"""Tests for bounded, protected rejected-frame capture."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import stat
import tempfile
import unittest

ROOT = Path(__file__).parents[1]
MODULE_PATH = ROOT / "custom_components" / "vlm_occupancy" / "debug_capture.py"
spec = importlib.util.spec_from_file_location(
    "vlm_occupancy_debug_capture", MODULE_PATH
)
assert spec is not None and spec.loader is not None
debug_capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(debug_capture)


class DebugCaptureTests(unittest.TestCase):
    """Keep only one private debug image at a time."""

    def test_capture_is_protected_and_overwrites_previous_format(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_root:
            directory = Path(temporary_root) / "vlm_occupancy_debug"

            first_path = Path(
                debug_capture.save_rejected_frame(
                    str(directory), b"jpeg content", "image/jpeg"
                )
            )
            self.assertEqual(first_path.name, "latest_rejected.jpg")
            self.assertEqual(first_path.read_bytes(), b"jpeg content")
            self.assertEqual(stat.S_IMODE(directory.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE(first_path.stat().st_mode), 0o600)

            second_path = Path(
                debug_capture.save_rejected_frame(
                    str(directory), b"png content", "image/png; charset=binary"
                )
            )
            self.assertEqual(second_path.name, "latest_rejected.png")
            self.assertEqual(second_path.read_bytes(), b"png content")
            self.assertFalse(first_path.exists())
            self.assertEqual(
                [path.name for path in directory.glob("latest_rejected.*")],
                ["latest_rejected.png"],
            )


if __name__ == "__main__":
    unittest.main()
