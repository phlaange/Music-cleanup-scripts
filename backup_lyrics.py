#!/usr/bin/env python3
"""
backup_lyrics.py — Save the lyrics tag of MP3, M4A, and FLAC files to a .bak text file.

The .bak file is written alongside the audio file with the same base name.

Usage:
  python backup_lyrics.py "K:\Music"
  python backup_lyrics.py                    # prompts
  python backup_lyrics.py "K:\Music" --overwrite

  Files with no lyrics tag are skipped cleanly. The .bak sits alongside the audio file with the same stem, e.g. 01. Love in a Vacuum.bak.

Requires:
    pip install mutagen
"""

import sys
import argparse
from pathlib import Path

try:
    from mutagen.id3 import ID3, ID3NoHeaderError
    from mutagen.mp4 import MP4
    from mutagen.flac import FLAC
except ImportError:
    sys.exit("Missing dependency: pip install mutagen")

AUDIO_EXTENSIONS = (".mp3", ".m4a", ".flac")


def read_lyrics_mp3(path: Path) -> str | None:
    try:
        tags = ID3(path)
    except ID3NoHeaderError:
        return None
    frames = tags.getall("USLT")
    return str(frames[0]) if frames else None


def read_lyrics_m4a(path: Path) -> str | None:
    tags = MP4(path)
    values = tags.get("©lyr")
    return str(values[0]) if values else None


def read_lyrics_flac(path: Path) -> str | None:
    tags = FLAC(path)
    values = tags.get("lyrics")
    return str(values[0]) if values else None


READERS = {
    ".mp3": read_lyrics_mp3,
    ".m4a": read_lyrics_m4a,
    ".flac": read_lyrics_flac,
}


def backup_lyrics_for_file(path: Path, overwrite: bool) -> str:
    bak_path = path.with_suffix(".bak")

    if bak_path.exists() and not overwrite:
        return "skipped (.bak already exists)"

    reader = READERS.get(path.suffix.lower())
    if reader is None:
        return "skipped (unsupported format)"

    try:
        lyrics = reader(path)
    except Exception as exc:
        return f"error reading tags: {exc}"

    if not lyrics or not lyrics.strip():
        return "skipped (no lyrics tag)"

    try:
        bak_path.write_text(lyrics, encoding="utf-8")
    except PermissionError:
        return "error: permission denied"
    except OSError as exc:
        return f"error: {exc}"

    return "saved"


def process_folder(root: Path, overwrite: bool = False) -> None:
    audio_files = sorted(
        f for f in root.rglob("*") if f.suffix.lower() in AUDIO_EXTENSIONS
    )

    if not audio_files:
        print("No audio files found.")
        return

    width = len(str(len(audio_files)))
    for i, audio in enumerate(audio_files, 1):
        relative = audio.relative_to(root)
        status = backup_lyrics_for_file(audio, overwrite=overwrite)
        print(f"[{i:{width}d}/{len(audio_files)}] {relative}  ->  {status}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Back up lyrics tags from MP3, M4A, and FLAC files to .bak text files."
    )
    parser.add_argument(
        "folder",
        nargs="?",
        help="Root folder to search for audio files (prompted if omitted).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing .bak files.",
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
    process_folder(root, overwrite=args.overwrite)
    print("\nDone.")


if __name__ == "__main__":
    main()
