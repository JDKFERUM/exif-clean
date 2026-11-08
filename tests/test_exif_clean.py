from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from exif_clean.cli import main
from exif_clean.jpeg import EXIF_HEADER, JpegError, XMP_HEADER, strip_metadata

SOI = b"\xff\xd8"
EOI = b"\xff\xd9"
SCAN_DATA = b"\x12\x34\x56\xff\x00\x78"
JFIF = b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"


def segment(marker: int, payload: bytes) -> bytes:
    return bytes([0xFF, marker]) + (len(payload) + 2).to_bytes(2, "big") + payload


def jpeg_with_metadata() -> bytes:
    sos = b"\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00"
    return (
        SOI
        + segment(0xE0, JFIF)
        + segment(0xE1, EXIF_HEADER + b"\x00" * 40)
        + segment(0xE1, XMP_HEADER + b"<x/>")
        + sos
        + SCAN_DATA
        + EOI
    )


WORK = Path(__file__).resolve().parents[1] / ".test-work"


@pytest.fixture
def workdir() -> Path:
    WORK.mkdir(exist_ok=True)
    path = WORK / f"case-{uuid.uuid4().hex[:10]}"
    path.mkdir()
    return path


def test_removes_exif_and_xmp() -> None:
    cleaned, removed = strip_metadata(jpeg_with_metadata())
    assert removed == ["EXIF", "XMP"]
    assert EXIF_HEADER not in cleaned
    assert XMP_HEADER not in cleaned


def test_keeps_image_data_intact() -> None:
    original = jpeg_with_metadata()
    cleaned, _ = strip_metadata(original)
    assert cleaned.startswith(SOI)
    assert cleaned.endswith(EOI)
    assert JFIF in cleaned
    assert SCAN_DATA in cleaned
    assert len(cleaned) < len(original)


def test_keep_xmp_flag_keeps_xmp_only() -> None:
    cleaned, removed = strip_metadata(jpeg_with_metadata(), keep_xmp=True)
    assert removed == ["EXIF"]
    assert XMP_HEADER in cleaned
    assert EXIF_HEADER not in cleaned


def test_clean_file_reports_nothing() -> None:
    plain = SOI + segment(0xE0, JFIF) + b"\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00" + SCAN_DATA + EOI
    cleaned, removed = strip_metadata(plain)
    assert removed == []
    assert cleaned == plain


def test_not_a_jpeg_raises() -> None:
    with pytest.raises(JpegError):
        strip_metadata(b"GIF89a")


def test_truncated_segment_raises() -> None:
    broken = SOI + b"\xff\xe1\x00\x40" + b"short"
    with pytest.raises(JpegError):
        strip_metadata(broken)


def test_cli_writes_clean_copy(workdir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source = workdir / "photo.jpg"
    source.write_bytes(jpeg_with_metadata())

    assert main([str(source)]) == 0
    target = workdir / "photo.clean.jpg"
    assert target.is_file()
    assert EXIF_HEADER not in target.read_bytes()
    assert "removed EXIF, XMP" in capsys.readouterr().out


def test_cli_dry_run_writes_nothing(workdir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source = workdir / "photo.jpg"
    source.write_bytes(jpeg_with_metadata())

    assert main([str(source), "--dry-run"]) == 0
    assert not (workdir / "photo.clean.jpg").exists()
    assert "would remove" in capsys.readouterr().out


def test_cli_in_place_overwrites(workdir: Path) -> None:
    source = workdir / "photo.jpg"
    source.write_bytes(jpeg_with_metadata())
    before = source.stat().st_size

    assert main([str(source), "--in-place"]) == 0
    assert source.stat().st_size < before
    assert EXIF_HEADER not in source.read_bytes()


def test_cli_reports_files_without_metadata(workdir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    plain = workdir / "plain.jpg"
    plain.write_bytes(SOI + segment(0xE0, JFIF) + b"\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00" + SCAN_DATA + EOI)

    assert main([str(plain)]) == 0
    assert "no metadata found" in capsys.readouterr().out


def test_cli_skips_broken_files(workdir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    broken = workdir / "broken.jpg"
    broken.write_bytes(b"not a jpeg")

    assert main([str(broken)]) == 0
    assert "skipped" in capsys.readouterr().err
