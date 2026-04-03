#!/usr/bin/env python3
r"""
strip_lrc_timestamps.py — Remove LRC timestamps from embedded lyrics tags,
leaving plain unsynced text.

Processes the lyrics field of MP3 (USLT), M4A (©lyr), and FLAC (LYRICS).
Files whose lyrics contain no timestamps are skipped unchanged.

Usage:
  python strip_lrc_timestamps.py "K:\Music"
  python strip_lrc_timestamps.py               # prompts for path
  python strip_lrc_timestamps.py "K:\Music" --overwrite

Requires:
    pip install mutagen
"""

import re
import sys
import argparse
from pathlib import Path

try:
    from mutagen.id3 import ID3, USLT, ID3NoHeaderError
    from mutagen.mp4 import MP4
    from mutagen.flac import FLAC
except ImportError:
    sys.exit("Missing dependency: pip install mutagen")

AUDIO_EXTENSIONS = (".mp3", ".m4a", ".flac")

# Timed LRC line: [mm:ss.xx] or [mm:ss.xxx]
_TIMED_RE = re.compile(r"^\[(\d{1,3}):(\d{2})\.(\d{2,3})\](.*)")
# LRC metadata tag: [ar:...], [ti:...], [al:...], [by:...], [offset:...], etc.
_META_RE = re.compile(r"^\[[a-zA-Z]+:[^\]]*\]$")


def has_timestamps(text: str) -> bool:
    return any(_TIMED_RE.match(line.strip()) for line in text.splitlines())


def strip_timestamps(text: str) -> str:
    """Remove LRC timing and metadata lines; keep the lyric text only."""
    result = []
    for line in text.splitlines():
        stripped = line.strip()
        m = _TIMED_RE.match(stripped)
        if m:
            lyric = m.group(4).strip()
            result.append(lyric)
        elif _META_RE.match(stripped):
            pass  # drop LRC metadata tags entirely
        else:
            result.append(line.rstrip())
    # Collapse runs of more than one blank line
    cleaned = re.sub(r"\n{3,}", "\n\n", "\n".join(result))
    return cleaned.strip()


def process_mp3(path: Path, overwrite: bool) -> str:
    try:
        try:
            tags = ID3(path)
        except ID3NoHeaderError:
            return "skipped (no ID3 tags)"

        frames = tags.getall("USLT")
        if not frames:
            return "skipped (no USLT frame)"

        frame = frames[0]
        text = str(frame)

        if not has_timestamps(text):
            return "skipped (no timestamps in USLT)"

        cleaned = strip_timestamps(text)
        tags.delall("USLT")
        tags.add(USLT(encoding=3, lang=frame.lang, desc=frame.desc, text=cleaned))
        tags.save(path)
        return "saved"
    except Exception as exc:
        return f"error: {exc}"


def process_m4a(path: Path, overwrite: bool) -> str:
    try:
        tags = MP4(path)
        values = tags.get("©lyr")
        if not values:
            return "skipped (no ©lyr tag)"

        text = str(values[0])
        if not has_timestamps(text):
            return "skipped (no timestamps in ©lyr)"

        tags["©lyr"] = [strip_timestamps(text)]
        tags.save()
        return "saved"
    except Exception as exc:
        return f"error: {exc}"


def process_flac(path: Path, overwrite: bool) -> str:
    try:
        tags = FLAC(path)
        values = tags.get("lyrics")
        if not values:
            return "skipped (no LYRICS tag)"

        text = str(values[0])
        if not has_timestamps(text):
            return "skipped (no timestamps in LYRICS)"

        tags["lyrics"] = strip_timestamps(text)
        tags.save()
        return "saved"
    except Exception as exc:
        return f"error: {exc}"


PROCESSORS = {
    ".mp3": process_mp3,
    ".m4a": process_m4a,
    ".flac": process_flac,
}


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
        processor = PROCESSORS[audio.suffix.lower()]
        status = processor(audio, overwrite)
        print(f"[{i:{width}d}/{len(audio_files)}] {relative}  ->  {status}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Strip LRC timestamps from embedded lyrics tags (USLT, ©lyr, LYRICS)."
    )
    parser.add_argument(
        "folder",
        nargs="?",
        help="Root folder to search for audio files (prompted if omitted).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Reserved for future use; included for interface consistency.",
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
