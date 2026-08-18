"""Canonical image policy shared by library and gateway entry points."""

from __future__ import annotations

# Keep these defaults in one place.  DSH may reject earlier for UX, but the
# gateway remains the authoritative enforcement boundary for untrusted input.
MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_IMAGE_PIXELS = 4096 * 4096
MAX_IMAGES_PER_REQUEST = 4
SUPPORTED_IMAGE_FORMATS = ("JPEG", "PNG", "WEBP")
