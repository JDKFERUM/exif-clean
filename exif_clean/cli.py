"""Command line interface for exif-clean."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from . import __version__
from .jpeg import JpegError, strip_metadata


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="exif-clean",
        description="Remove EXIF and XMP metadata from JPEG files before sharing them.",
    )
    parser.add_argument("paths", nargs="+", type=Path, help="JPEG files to clean")
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="overwrite the original files instead of writing *.clean.jpg next to them",
    )
    parser.add_argument("--dry-run", action="store_true", help="report what would be removed, write nothing")
    parser.add_argument("--keep-xmp", action="store_true", help="remove EXIF but keep XMP metadata")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def _target_for(path: Path, in_place: bool) -> Path:
    if in_place:
        return path
    return path.with_suffix(".clean.jpg")


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    cleaned_files = 0
    for path in args.paths:
        if not path.is_file():
            print(f"{path}: no such file", file=sys.stderr)
            continue
        try:
            data = path.read_bytes()
            cleaned, removed = strip_metadata(data, keep_xmp=args.keep_xmp)
        except (OSError, JpegError) as error:
            print(f"{path}: skipped ({error})", file=sys.stderr)
            continue

        if not removed:
            print(f"{path}: no metadata found")
            continue

        cleaned_files += 1
        saved = len(data) - len(cleaned)
        labels = ", ".join(removed)
        if args.dry_run:
            print(f"{path}: would remove {labels} ({saved} bytes)")
            continue

        target = _target_for(path, args.in_place)
        try:
            target.write_bytes(cleaned)
        except OSError as error:
            print(f"{path}: cannot write {target} ({error})", file=sys.stderr)
            continue
        print(f"{path}: removed {labels} ({saved} bytes) -> {target}")

    if cleaned_files == 0:
        print("exif-clean: nothing to do")
    return 0


def entry() -> None:  # pragma: no cover - console script wrapper
    raise SystemExit(main())
