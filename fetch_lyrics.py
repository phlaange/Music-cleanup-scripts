#!/usr/bin/env python3
r"""
fetch_lyrics.py — Download synced lyrics (.lrc) for MP3, M4A, and FLAC files in a folder hierarchy.

Skips files that already have a .lrc sidecar. Use --overwrite to replace them.

Usage:
  python fetch_lyrics.py "K:\Music"
  python fetch_lyrics.py                        # prompts for path
  python fetch_lyrics.py "K:\Music" --overwrite

Requires:
    pip install syncedlyrics mutagen
"""

import sys
import argparse
from pathlib import Path

try:
    import syncedlyrics
except ImportError:
    sys.exit("Missing dependency: pip install syncedlyrics")

try:
    from mutagen import File as MutagenFile
except ImportError:
    sys.exit("Missing dependency: pip install mutagen")

AUDIO_EXTENSIONS = (".mp3", ".m4a", ".flac")


def get_track_info(path: Path) -> tuple[str, str]:
    """Return (artist, title) from tags, or empty strings if unavailable.

    Uses mutagen's easy interface which normalises keys across MP3 (ID3),
    M4A (iTunes), and FLAC (Vorbis comment) into lowercase 'artist'/'title'.
    """
    try:
        tags = MutagenFile(path, easy=True)
        if tags is None:
            return "", ""
        artist = str(tags.get("artist", [""])[0]).strip()
        title = str(tags.get("title", [""])[0]).strip()
        return artist, title
    except Exception:
        return "", ""


def build_search_term(artist: str, title: str, filename_stem: str) -> str:
    """Build the best search string we can from available metadata."""
    if artist and title:
        return f"{artist} {title}"
    if title:
        return title
    # Fall back to the filename without extension
    return filename_stem


def fetch_lyrics_for_file(path: Path, overwrite: bool = False) -> str:
    """Fetch and save an .lrc file for the given audio file. Returns a status string."""
    lrc_path = path.with_suffix(".lrc")

    if lrc_path.exists() and not overwrite:
        return "skipped (LRC already exists)"

    artist, title = get_track_info(path)
    search_term = build_search_term(artist, title, path.stem)

    try:
        lyrics = syncedlyrics.search(search_term)
    except Exception as exc:
        return f"error during search: {exc}"

    if not lyrics:
        # Try a plain filename search as a fallback if metadata was used first
        if search_term != path.stem:
            try:
                lyrics = syncedlyrics.search(path.stem)
            except Exception:
                pass

    if not lyrics:
        return "not found"

    try:
        lrc_path.write_text(lyrics, encoding="utf-8")
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
        status = fetch_lyrics_for_file(audio, overwrite=overwrite)
        print(f"[{i:{width}d}/{len(audio_files)}] {relative}  ->  {status}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch synced lyrics (.lrc) for MP3, M4A, and FLAC files."
    )
    parser.add_argument(
        "folder",
        nargs="?",
        help="Root folder to search for audio files (prompted if omitted).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing .lrc files.",
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
