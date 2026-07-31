"""Opt-in, bounded storage for the latest rejected camera frame."""

from __future__ import annotations

import os
from pathlib import Path

CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def save_rejected_frame(directory: str, content: bytes, content_type: str) -> str:
    """Atomically overwrite the single protected rejected-frame file."""
    target_directory = Path(directory)
    target_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    target_directory.chmod(0o700)

    normalized_content_type = content_type.partition(";")[0].strip().lower()
    extension = CONTENT_TYPE_EXTENSIONS.get(normalized_content_type, ".bin")
    target = target_directory / f"latest_rejected{extension}"
    temporary = target_directory / ".latest_rejected.tmp"
    flags = os.O_CREAT | os.O_WRONLY | os.O_TRUNC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor: int | None = None
    try:
        descriptor = os.open(temporary, flags, 0o600)
        with os.fdopen(descriptor, "wb") as file_handle:
            descriptor = None
            file_handle.write(content)
        temporary.chmod(0o600)
        temporary.replace(target)
        target.chmod(0o600)
    except OSError:
        if descriptor is not None:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)
        raise

    for stale in target_directory.glob("latest_rejected.*"):
        if stale != target:
            stale.unlink(missing_ok=True)
    return os.fspath(target)
