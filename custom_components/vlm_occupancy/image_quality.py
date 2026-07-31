"""Small local checks that keep unusable camera frames away from the VLM."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from math import sqrt
import warnings

from PIL import Image

MAX_DECODED_PIXELS = 32_000_000
SAMPLE_SIZE = (64, 64)
BLACK_LEVEL = 24
MAX_BLACK_PIXEL_RATIO = 0.98
MAX_DARK_MEAN_LUMA = 24
MAX_DARK_CONTRAST = 8


@dataclass(frozen=True, slots=True)
class ImageQuality:
    """Sanitized image measurements suitable for debug logs."""

    usable: bool
    reason: str
    width: int | None = None
    height: int | None = None
    mean_luma: float | None = None
    contrast: float | None = None
    black_ratio: float | None = None


def inspect_image(content: bytes) -> ImageQuality:
    """Inspect an image without retaining decoded pixels or sensitive content."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(content)) as image:
                width, height = image.size
                if width <= 0 or height <= 0:
                    return ImageQuality(False, "invalid_dimensions", width, height)
                if width * height > MAX_DECODED_PIXELS:
                    return ImageQuality(False, "decoded_image_too_large", width, height)
                image.draft("L", SAMPLE_SIZE)
                image.thumbnail(SAMPLE_SIZE)
                histogram = image.convert("L").histogram()
    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        OSError,
        ValueError,
    ):
        return ImageQuality(False, "invalid_image")

    pixel_count = sum(histogram)
    if pixel_count == 0:
        return ImageQuality(False, "empty_image", width, height)

    mean_luma = (
        sum(level * count for level, count in enumerate(histogram)) / pixel_count
    )
    variance = (
        sum(((level - mean_luma) ** 2) * count for level, count in enumerate(histogram))
        / pixel_count
    )
    contrast = sqrt(variance)
    black_ratio = sum(histogram[: BLACK_LEVEL + 1]) / pixel_count
    measurements = {
        "width": width,
        "height": height,
        "mean_luma": round(mean_luma, 2),
        "contrast": round(contrast, 2),
        "black_ratio": round(black_ratio, 4),
    }
    if black_ratio >= MAX_BLACK_PIXEL_RATIO:
        return ImageQuality(False, "nearly_black", **measurements)
    if mean_luma <= MAX_DARK_MEAN_LUMA and contrast <= MAX_DARK_CONTRAST:
        return ImageQuality(False, "dark_low_contrast", **measurements)
    return ImageQuality(True, "usable", **measurements)


def is_usable_image(content: bytes) -> bool:
    """Return whether an image contains enough visual information for inference."""
    return inspect_image(content).usable
