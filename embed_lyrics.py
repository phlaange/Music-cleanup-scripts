#!/usr/bin/env python3
"""
embed_lyrics.py — Copy .lrc file contents into the lyrics tag of matching audio files.

Supports MP3, M4A, and FLAC. Requires a .lrc file with the same base name as the
audio file in the same directory.

  ┌────────┬──────────────────────────────────────────────────┐
  │ Format │                       Tag                        │
  ├────────┼──────────────────────────────────────────────────┤
  │ MP3    │ USLT (unsynchronized lyrics) or SYLT (synced)    │
  ├────────┼──────────────────────────────────────────────────┤
  │ M4A    │ ©lyr (iTunes lyrics field)                       │
  ├────────┼──────────────────────────────────────────────────┤
  │ FLAC   │ LYRICS (Vorbis comment)                          │
  └────────┴──────────────────────────────────────────────────┘

Usage:
  python embed_lyrics.py "K:\Music"
  python embed_lyrics.py          # prompts for path
  python embed_lyrics.py "K:\Music" --overwrite
  python embed_lyrics.py "K:\Music" --language fra
  python embed_lyrics.py "K:\Music" --sylt        # MP3: write SYLT instead of USLT

  Defaults to eng if --language is omitted.

Requires:
    pip install mutagen
"""

import re
import sys
import argparse
from pathlib import Path

try:
    from mutagen.id3 import ID3, USLT, SYLT, ID3NoHeaderError
    from mutagen.mp4 import MP4
    from mutagen.flac import FLAC
except ImportError:
    sys.exit("Missing dependency: pip install mutagen")

# Matches a timed LRC line: [mm:ss.xx] or [mm:ss.xxx]
_LRC_LINE_RE = re.compile(r"^\[(\d{1,3}):(\d{2})\.(\d{2,3})\](.*)")


def parse_lrc(lyrics: str) -> list[tuple[str, int]]:
    """Parse LRC text into a list of (line_text, timestamp_ms) tuples for SYLT."""
    result = []
    for line in lyrics.splitlines():
        m = _LRC_LINE_RE.match(line.strip())
        if not m:
            continue
        minutes, seconds, frac, text = m.groups()
        # frac may be 2 (centiseconds) or 3 (milliseconds) digits — normalise to ms
        ms = (int(minutes) * 60 + int(seconds)) * 1000 + int(frac.ljust(3, "0"))
        result.append((text.strip(), ms))
    return result

AUDIO_EXTENSIONS = (".mp3", ".m4a", ".flac")


def embed_mp3(path: Path, lyrics: str, overwrite: bool, lang: str, sylt: bool) -> str:
    try:
        try:
            tags = ID3(path)
        except ID3NoHeaderError:
            tags = ID3()

        if sylt:
            existing = tags.getall("SYLT")
            if existing and not overwrite:
                return "skipped (SYLT tag already set)"
            synced = parse_lrc(lyrics)
            if not synced:
                return "skipped (no timed lines found in LRC for SYLT)"
            tags.delall("SYLT")
            tags.add(SYLT(encoding=3, lang=lang, format=2, type=1, desc="", text=synced))
        else:
            existing = tags.getall("USLT")
            if existing and not overwrite:
                return "skipped (lyrics tag already set)"
            tags.delall("USLT")
            tags.add(USLT(encoding=3, lang=lang, desc="", text=lyrics))

        tags.save(path)
        return "saved"
    except Exception as exc:
        return f"error: {exc}"


def embed_m4a(path: Path, lyrics: str, overwrite: bool, lang: str, sylt: bool) -> str:
    # M4A (iTunes) has no standard per-field language tag for lyrics; lang is not stored.
    try:
        tags = MP4(path)
        if "©lyr" in tags and not overwrite:
            return "skipped (lyrics tag already set)"
        tags["©lyr"] = [lyrics]
        tags.save()
        return "saved"
    except Exception as exc:
        return f"error: {exc}"


def embed_flac(path: Path, lyrics: str, overwrite: bool, lang: str, sylt: bool) -> str:
    try:
        tags = FLAC(path)
        if tags.get("lyrics") and not overwrite:
            return "skipped (lyrics tag already set)"
        tags["lyrics"] = lyrics
        tags["language"] = lang
        tags.save()
        return "saved"
    except Exception as exc:
        return f"error: {exc}"


EMBEDDERS = {
    ".mp3": embed_mp3,
    ".m4a": embed_m4a,
    ".flac": embed_flac,
}


def embed_lyrics_for_file(path: Path, overwrite: bool, lang: str, sylt: bool) -> str:
    lrc_path = path.with_suffix(".lrc")
    if not lrc_path.exists():
        return "skipped (no .lrc file)"

    lyrics = lrc_path.read_text(encoding="utf-8").strip()
    if not lyrics:
        return "skipped (.lrc file is empty)"

    embedder = EMBEDDERS.get(path.suffix.lower())
    if embedder is None:
        return "skipped (unsupported format)"

    return embedder(path, lyrics, overwrite, lang, sylt)


def process_folder(root: Path, overwrite: bool = False, lang: str = "eng", sylt: bool = False) -> None:
    audio_files = sorted(
        f for f in root.rglob("*") if f.suffix.lower() in AUDIO_EXTENSIONS
    )

    if not audio_files:
        print("No audio files found.")
        return

    width = len(str(len(audio_files)))
    for i, audio in enumerate(audio_files, 1):
        relative = audio.relative_to(root)
        status = embed_lyrics_for_file(audio, overwrite=overwrite, lang=lang, sylt=sylt)
        print(f"[{i:{width}d}/{len(audio_files)}] {relative}  ->  {status}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Embed .lrc file contents into the lyrics tag of MP3, M4A, and FLAC files."
    )
    parser.add_argument(
        "folder",
        nargs="?",
        help="Root folder to search for audio files (prompted if omitted).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing lyrics tags.",
    )
    parser.add_argument(
        "--language",
        default="eng",
        metavar="LANG",
        help="ISO 639-2 three-letter language code (default: eng).",
    )
    parser.add_argument(
        "--sylt",
        action="store_true",
        help="MP3 only: write a SYLT (synced lyrics) frame instead of USLT.",
    )
    args = parser.parse_args()

    if len(args.language) != 3 or not args.language.isalpha():
        sys.exit("--language must be a 3-letter ISO 639-2 code, e.g. eng, fra, deu.")

    folder = args.folder
    if not folder:
        folder = input("Enter the folder path: ").strip().strip('"').strip("'")

    root = Path(folder)
    if not root.exists():
        sys.exit(f"Path does not exist: {root}")
    if not root.is_dir():
        sys.exit(f"Not a directory: {root}")

    lang = args.language.lower()
    print(f"Scanning: {root.resolve()}\n")
    process_folder(root, overwrite=args.overwrite, lang=lang, sylt=args.sylt)
    print("\nDone.")


if __name__ == "__main__":
    main()
