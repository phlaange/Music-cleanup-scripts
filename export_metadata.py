#!/usr/bin/env python3
r"""
export_metadata.py — Export music file metadata to a CSV.

Outputs path, artist, album, title, and bitrate for every MP3, M4A, and FLAC
file found under the given folder hierarchy.

Usage:
  python export_metadata.py "K:\Music"
  python export_metadata.py                          # prompts for path
  python export_metadata.py "K:\Music" --output metadata.csv

If --output is omitted the CSV is written to metadata.csv inside the scanned folder.

Requires:
    pip install mutagen
"""

import sys
import csv
import argparse
from pathlib import Path

try:
    from mutagen import File as MutagenFile
    from mutagen.mp3 import MP3
    from mutagen.mp4 import MP4
    from mutagen.flac import FLAC
except ImportError:
    sys.exit("Missing dependency: pip install mutagen")

AUDIO_EXTENSIONS = (".mp3", ".m4a", ".flac")


def get_metadata(path: Path) -> dict:
    result = {"path": str(path), "artist": "", "album": "", "title": "", "bitrate": ""}

    try:
        tags = MutagenFile(path, easy=True)
        if tags is not None:
            result["artist"] = str(tags.get("artist", [""])[0]).strip()
            result["album"]  = str(tags.get("album",  [""])[0]).strip()
            result["title"]  = str(tags.get("title",  [""])[0]).strip()
    except Exception:
        pass

    try:
        suffix = path.suffix.lower()
        if suffix == ".mp3":
            info = MP3(path).info
            result["bitrate"] = f"{info.bitrate // 1000} kbps"
        elif suffix == ".m4a":
            info = MP4(path).info
            result["bitrate"] = f"{info.bitrate // 1000} kbps"
        elif suffix == ".flac":
            info = FLAC(path).info
            result["bitrate"] = f"{info.bits_per_sample}bit/{info.sample_rate // 1000}kHz"
    except Exception:
        pass

    return result


def process_folder(root: Path, output: Path) -> None:
    audio_files = sorted(
        f for f in root.rglob("*") if f.suffix.lower() in AUDIO_EXTENSIONS
    )

    if not audio_files:
        print("No audio files found.")
        return

    fieldnames = ["path", "artist", "album", "title", "bitrate"]
    width = len(str(len(audio_files)))

    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for i, audio in enumerate(audio_files, 1):
            row = get_metadata(audio)
            writer.writerow(row)
            print(f"[{i:{width}d}/{len(audio_files)}] {audio.relative_to(root)}")

    print(f"\nWritten to {output}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export music file metadata to a CSV."
    )
    parser.add_argument(
        "folder",
        nargs="?",
        help="Root folder to search for audio files (prompted if omitted).",
    )
    parser.add_argument(
        "--output",
        default=None,
        metavar="FILE",
        help="Output CSV file (default: metadata.csv inside the scanned folder).",
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

    output = Path(args.output) if args.output else root / "metadata.csv"
    print(f"Scanning: {root.resolve()}\n")
    process_folder(root, output)


if __name__ == "__main__":
    main()
