"""Strip metadata segments from JPEG files without any external dependency.

Windows, macOS and Linux all write EXIF blocks with camera model, timestamps
and GPS coordinates into JPEG files.  Sharing a photo as-is shares that too.
This module removes the metadata segments and keeps the compressed image data
byte for byte.
"""

from __future__ import annotations

SOI = b"\xff\xd8"
APP1 = 0xE1
SOS = 0xDA
EOI = 0xD9

EXIF_HEADER = b"Exif\x00\x00"
XMP_HEADER = b"http://ns.adobe.com/xap/1.0/\x00"


class JpegError(ValueError):
    """Raised when the input is not a JPEG we can walk safely."""


def strip_metadata(data: bytes, keep_xmp: bool = False) -> tuple[bytes, list[str]]:
    """Return ``(cleaned_bytes, removed_labels)``.

    ``removed_labels`` is empty when the file carried no metadata.  The scan
    data after the start-of-scan marker is copied verbatim, so the picture
    itself is never re-encoded.
    """
    if not data.startswith(SOI):
        raise JpegError("not a JPEG file (missing SOI marker)")

    out = bytearray(SOI)
    removed: list[str] = []
    pos = 2

    while pos < len(data):
        start = pos
        if data[pos] != 0xFF:
            raise JpegError(f"expected a marker at offset {pos}")
        while pos < len(data) and data[pos] == 0xFF:
            pos += 1
        if pos >= len(data):
            raise JpegError("truncated marker")
        marker = data[pos]
        pos += 1

        if marker == EOI:
            out += data[start:pos]
            return bytes(out), removed
        if marker == SOS:
            out += data[start:]
            return bytes(out), removed

        if pos + 2 > len(data):
            raise JpegError("truncated segment length")
        length = int.from_bytes(data[pos : pos + 2], "big")
        if length < 2:
            raise JpegError("invalid segment length")
        end = pos + length
        if end > len(data):
            raise JpegError("truncated segment")

        payload = data[pos + 2 : end]
        drop = None
        if marker == APP1:
            if payload.startswith(EXIF_HEADER):
                drop = "EXIF"
            elif payload.startswith(XMP_HEADER) and not keep_xmp:
                drop = "XMP"

        if drop is None:
            out += data[start:end]
        else:
            removed.append(drop)
        pos = end

    raise JpegError("unexpected end of file (no end-of-image marker)")
