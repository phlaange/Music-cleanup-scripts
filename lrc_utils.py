"""
lrc_utils.py — Shared LRC parsing and formatting utilities.

All timestamps are handled internally as centiseconds (cs).
LRC format uses centiseconds: [mm:ss.cc]

Public API:
  TIMED_RE        — compiled regex matching a timed LRC line
  META_RE         — compiled regex matching an LRC metadata tag
  parse_cs(m)     — convert a TIMED_RE match to centiseconds
  cs_to_lrc(cs)   — format centiseconds as "[mm:ss.cc]"
  has_timestamps(text) -> bool
  strip_timestamps(text) -> str
  parse_lrc(text) -> list[tuple[str, int]]  — (lyric, cs) pairs
"""

import re

# Matches a timed LRC line: [mm:ss.cc] or [mm:ss.ccc]
# Groups: (minutes, seconds, frac, lyric_text)
TIMED_RE = re.compile(r"^\[(\d{1,3}):(\d{2})\.(\d{2,3})\](.*)")

# Matches an LRC metadata tag: [ar:...], [ti:...], [al:...], [by:...], [offset:...], etc.
META_RE = re.compile(r"^\[[a-zA-Z]+:[^\]]*\]$")


def parse_cs(m: re.Match) -> int:
    """Return centiseconds from a TIMED_RE match."""
    minutes, seconds, frac, _ = m.groups()
    # frac may be 2 digits (centiseconds) or 3 digits (milliseconds) — normalise to cs
    cs = int(frac) // 10 if len(frac) == 3 else int(frac)
    return int(minutes) * 6000 + int(seconds) * 100 + cs


def cs_to_lrc(cs: int) -> str:
    """Format centiseconds as an LRC timestamp string [mm:ss.cc]."""
    cs = max(0, cs)
    minutes, remainder = divmod(cs, 6000)
    seconds, centiseconds = divmod(remainder, 100)
    return f"[{minutes:02d}:{seconds:02d}.{centiseconds:02d}]"


def has_timestamps(text: str) -> bool:
    """Return True if any line in text matches the timed LRC format."""
    return any(TIMED_RE.match(line.strip()) for line in text.splitlines())


def strip_timestamps(text: str) -> str:
    """Remove LRC timing tags and metadata lines, returning plain lyric text."""
    result = []
    for line in text.splitlines():
        stripped = line.strip()
        m = TIMED_RE.match(stripped)
        if m:
            result.append(m.group(4).strip())
        elif META_RE.match(stripped):
            pass  # drop LRC metadata tags entirely
        else:
            result.append(line.rstrip())
    cleaned = re.sub(r"\n{3,}", "\n\n", "\n".join(result))
    return cleaned.strip()


def parse_lrc(text: str) -> list[tuple[str, int]]:
    """Parse LRC text into (lyric, centiseconds) tuples, skipping non-timed lines."""
    result = []
    for line in text.splitlines():
        m = TIMED_RE.match(line.strip())
        if m:
            result.append((m.group(4).strip(), parse_cs(m)))
    return result
