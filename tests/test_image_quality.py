"""Tests for rejecting unusable camera frames before VLM inference."""

from __future__ import annotations

from io import BytesIO
import importlib.util
from pathlib import Path
import unittest

from PIL import Image, ImageDraw

ROOT = Path(__file__).parents[1]
MODULE_PATH = ROOT / "custom_components" / "vlm_occupancy" / "image_quality.py"
spec = importlib.util.spec_from_file_location(
    "vlm_occupancy_image_quality", MODULE_PATH
)
assert spec is not None and spec.loader is not None
image_quality = importlib.util.module_from_spec(spec)
spec.loader.exec_module(image_quality)


def _jpeg(image: Image.Image) -> bytes:
    output = BytesIO()
    image.save(output, format="JPEG")
    return output.getvalue()


class ImageQualityTests(unittest.TestCase):
    """Reject cold-camera frames without rejecting ordinary dark scenes."""

    def test_rejects_black_frame(self) -> None:
        self.assertFalse(
            image_quality.is_usable_image(_jpeg(Image.new("RGB", (320, 240))))
        )

    def test_rejects_nearly_black_frame(self) -> None:
        self.assertFalse(
            image_quality.is_usable_image(
                _jpeg(Image.new("RGB", (320, 240), (6, 6, 6)))
            )
        )

    def test_accepts_visible_dark_scene(self) -> None:
        image = Image.new("RGB", (320, 240), (8, 8, 8))
        ImageDraw.Draw(image).rectangle((80, 60, 240, 180), fill=(45, 45, 45))

        self.assertTrue(image_quality.is_usable_image(_jpeg(image)))

    def test_accepts_normal_frame(self) -> None:
        self.assertTrue(
            image_quality.is_usable_image(
                _jpeg(Image.new("RGB", (320, 240), (100, 120, 140)))
            )
        )

    def test_rejects_invalid_image(self) -> None:
        self.assertFalse(image_quality.is_usable_image(b"not an image"))


if __name__ == "__main__":
    unittest.main()
