#!/usr/bin/env python3
r"""
lrc_offset.py — Shift all timestamps in an .lrc file by a fixed offset.

Positive offset delays lyrics (they appear later); negative makes them earlier.
Timestamps that would go below zero are clamped to [00:00.00].

Usage:
  python lrc_offset.py "Smile.lrc" +2.5
  python lrc_offset.py "Smile.lrc" -0.03
  python lrc_offset.py                    # prompts for path and offset

Requires: no third-party dependencies
"""

import sys
import argparse
from pathlib import Path

from lrc_utils import TIMED_RE, parse_cs, cs_to_lrc


def shift_line(line: str, offset_cs: int) -> str:
    m = TIMED_RE.match(line.strip())
    if not m:
        return line
    new_cs = max(0, parse_cs(m) + offset_cs)
    return f"{cs_to_lrc(new_cs)}{m.group(4)}"


def process(path: Path, offset_cs: int) -> None:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    shifted = [shift_line(l.rstrip("\n\r"), offset_cs) + "\n" for l in lines]
    path.write_text("".join(shifted), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Shift .lrc timestamps by a fixed offset in seconds."
    )
    parser.add_argument("file",   nargs="?", help=".lrc file to adjust.")
    parser.add_argument("offset", nargs="?", help="Offset in seconds, e.g. +2.5 or -0.03.")
    args = parser.parse_args()

    path_str = args.file
    if not path_str:
        path_str = input("LRC file path: ").strip().strip('"').strip("'")

    path = Path(path_str)
    if not path.exists():
        sys.exit(f"File not found: {path}")
    if path.suffix.lower() != ".lrc":
        sys.exit(f"Not an .lrc file: {path}")

    offset_str = args.offset
    if not offset_str:
        offset_str = input("Offset in seconds (e.g. +2.5 or -0.03): ").strip()

    try:
        offset_sec = float(offset_str)
    except ValueError:
        sys.exit(f"Invalid offset: {offset_str!r}")

    offset_cs = round(offset_sec * 100)
    process(path, offset_cs)
    direction = "forward" if offset_cs > 0 else "back"
    print(f"Shifted {abs(offset_sec):.2f}s {direction}: {path}")


if __name__ == "__main__":
    main()
