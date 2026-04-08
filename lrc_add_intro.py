#!/usr/bin/env python3
r"""
lrc_add_intro.py — Prepend a [00:00.00] intro line to .lrc files that have
timestamps but don't already start at time zero.

This prevents players from showing "No lyrics" while waiting for the first
timed line to arrive.

Usage:
  python lrc_add_intro.py "K:\Music"
  python lrc_add_intro.py                       # prompts for path
  python lrc_add_intro.py "K:\Music" --overwrite   # replace existing [00:00.00] lines
  python lrc_add_intro.py "K:\Music" --text "♪"    # custom intro text (default: ** intro **)

Requires: no third-party dependencies
"""

import sys
import argparse
from pathlib import Path

from lrc_utils import TIMED_RE, parse_cs

_DEFAULT_INTRO = "---** INTRO **---"


def process_lrc(path: Path, intro_text: str, overwrite: bool) -> str:
    try:
        content = path.read_text(encoding="utf-8")
    except PermissionError:
        return "error: permission denied"
    except OSError as exc:
        return f"error: {exc}"

    lines = content.splitlines(keepends=True)

    # Collect all timed lines
    timed = [(i, TIMED_RE.match(l.strip())) for i, l in enumerate(lines)]
    timed = [(i, m) for i, m in timed if m]

    if not timed:
        return "skipped (no timestamps)"

    # Check whether any line is already at time zero
    zero_indices = [i for i, m in timed if parse_cs(m) == 0]

    if zero_indices and not overwrite:
        return "skipped ([00:00.00] already present)"

    intro_line = f"[00:00.00] {intro_text}\n"

    if zero_indices and overwrite:
        # Replace existing zero-time line(s) with the intro, keep only the first
        lines[zero_indices[0]] = intro_line
        for i in reversed(zero_indices[1:]):
            lines.pop(i)
    else:
        # Insert before the first timed line so metadata tags stay at the top
        first_timed_index = timed[0][0]
        lines.insert(first_timed_index, intro_line)

    try:
        path.write_text("".join(lines), encoding="utf-8")
    except PermissionError:
        return "error: permission denied"
    except OSError as exc:
        return f"error: {exc}"

    return "saved"


def process_folder(root: Path, intro_text: str, overwrite: bool) -> None:
    lrc_files = sorted(root.rglob("*.lrc"))

    if not lrc_files:
        print("No .lrc files found.")
        return

    width = len(str(len(lrc_files)))
    for i, lrc in enumerate(lrc_files, 1):
        relative = lrc.relative_to(root)
        status = process_lrc(lrc, intro_text=intro_text, overwrite=overwrite)
        print(f"[{i:{width}d}/{len(lrc_files)}] {relative}  ->  {status}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepend a [00:00.00] intro line to .lrc files that lack one."
    )
    parser.add_argument(
        "folder",
        nargs="?",
        help="Root folder to search for .lrc files (prompted if omitted).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing [00:00.00] lines instead of skipping.",
    )
    parser.add_argument(
        "--text",
        default=_DEFAULT_INTRO,
        metavar="TEXT",
        help=f'Intro line text (default: "{_DEFAULT_INTRO}").',
    )
    args = parser.parse_args()

    folder = args.folder
    if not folder:
        folder = input("Enter the folder path: ").strip().strip('"').strip("'")

    root = Path(folder)
    if not root.exists():
        sys.exit(f"Path does not exist: {root}")
    if not root.is_dir():
        sys.exit(f"Not a directory: {root}")

    print(f"Scanning: {root.resolve()}\n")
    process_folder(root, intro_text=args.text, overwrite=args.overwrite)
    print("\nDone.")


if __name__ == "__main__":
    main()
