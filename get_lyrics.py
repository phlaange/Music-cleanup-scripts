#!/usr/bin/env python3
r"""
get_lyrics.py — Fetch lyrics for a single track by title, artist, and album.

Lyrics are printed to stdout. Use --output to save to a file instead.

Usage:
  python get_lyrics.py --title "Feel" --artist "Robbie Williams" --album "Escapology"
  python get_lyrics.py                        # prompts for each field
  python get_lyrics.py --title "Feel" --output feel.lrc

Requires:
    pip install syncedlyrics
"""

import sys
import argparse
from pathlib import Path

try:
    import syncedlyrics
except ImportError:
    sys.exit("Missing dependency: pip install syncedlyrics")


def prompt_if_missing(value: str | None, label: str, required: bool = True) -> str:
    if value:
        return value.strip()
    while True:
        entered = input(f"{label}: ").strip()
        if entered or not required:
            return entered


def build_search_term(title: str, artist: str, album: str) -> list[str]:
    """Return search strings to try, most specific first."""
    terms = []
    if artist and title:
        terms.append(f"{artist} {title}")
    if title:
        terms.append(title)
    return terms


def fetch(title: str, artist: str, album: str) -> str | None:
    for term in build_search_term(title, artist, album):
        try:
            lyrics = syncedlyrics.search(term)
            if lyrics:
                return lyrics
        except Exception:
            pass
    return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch lyrics for a single track."
    )
    parser.add_argument("--title",  metavar="TITLE",  help="Track title.")
    parser.add_argument("--artist", metavar="ARTIST", help="Artist name.")
    parser.add_argument("--album",  metavar="ALBUM",  help="Album name (optional, used as context).")
    parser.add_argument(
        "--output",
        metavar="FILE",
        help="Save lyrics to this file instead of printing to stdout.",
    )
    args = parser.parse_args()

    title  = prompt_if_missing(args.title,  "Title",         required=True)
    artist = prompt_if_missing(args.artist, "Artist",        required=False)
    album  = prompt_if_missing(args.album,  "Album (enter to skip)", required=False)

    print(f"\nSearching for: {artist + ' — ' if artist else ''}{title}...")
    lyrics = fetch(title, artist, album)

    if not lyrics:
        sys.exit("Lyrics not found.")

    if args.output:
        out = Path(args.output)
        try:
            out.write_text(lyrics, encoding="utf-8")
            print(f"Saved to {out}")
        except OSError as exc:
            sys.exit(f"Could not write file: {exc}")
    else:
        print()
        print(lyrics)


if __name__ == "__main__":
    main()
