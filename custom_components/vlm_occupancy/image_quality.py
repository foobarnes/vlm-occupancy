"""Small local checks that keep unusable camera frames away from the VLM."""

from __future__ import annotations

from io import BytesIO
import warnings

from PIL import Image

MAX_DECODED_PIXELS = 32_000_000
SAMPLE_SIZE = (64, 64)
BLACK_LEVEL = 12
MAX_BLACK_PIXEL_RATIO = 0.98


def is_usable_image(content: bytes) -> bool:
    """Return false for corrupt, oversized, or overwhelmingly black images."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(content)) as image:
                width, height = image.size
                if width <= 0 or height <= 0 or width * height > MAX_DECODED_PIXELS:
                    return False
                image.draft("L", SAMPLE_SIZE)
                image.thumbnail(SAMPLE_SIZE)
                grayscale = image.convert("L")
                histogram = grayscale.histogram()
    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        OSError,
        ValueError,
    ):
        return False

    pixel_count = sum(histogram)
    if pixel_count == 0:
        return False
    black_pixels = sum(histogram[: BLACK_LEVEL + 1])
    return black_pixels / pixel_count < MAX_BLACK_PIXEL_RATIO
