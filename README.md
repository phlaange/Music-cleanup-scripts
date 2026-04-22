# Music Cleanup Scripts

A collection of Python scripts for fetching, embedding, and managing lyrics for a music library. Supports MP3, M4A, and FLAC.

Note: these scripts have been authored almost entirely by Claude Code and it is recommended that you read and understand them before using them.

## Dependencies

```bash
pip install syncedlyrics mutagen
```

---

## Scripts

### `fetch_lyrics.py`
Fetches synced lyrics (`.lrc` sidecar files) for audio files in a folder hierarchy using the `syncedlyrics` library. Reads artist and title from the file's tags; falls back to the filename if tags are missing.

```bash
python fetch_lyrics.py "K:\Music"
python fetch_lyrics.py                        # prompts for path
python fetch_lyrics.py "K:\Music" --overwrite
```

---

### `get_lyrics.py`
Fetches lyrics for a single track by title, artist, and album. Prints to stdout or saves to a file.

```bash
python get_lyrics.py --title "Feel" --artist "Robbie Williams" --album "Escapology"
python get_lyrics.py                          # prompts for each field
python get_lyrics.py --title "Feel" --output feel.lrc
```

---

### `backup_lyrics.py`
Saves the embedded lyrics tag of each audio file to a `.bak` plain-text file alongside it.

```bash
python backup_lyrics.py "K:\Music"
python backup_lyrics.py                       # prompts for path
python backup_lyrics.py "K:\Music" --overwrite
```

---

### `lrc_add_intro.py`
Prepends a `[00:00.00]` intro line to `.lrc` files that have timestamps but don't start at time zero. Prevents players from showing "No lyrics" while waiting for the first timed line. Files with no timestamps at all are left untouched.

```bash
python lrc_add_intro.py "K:\Music"
python lrc_add_intro.py                       # prompts for path
python lrc_add_intro.py "K:\Music" --overwrite          # replace existing [00:00.00] lines
python lrc_add_intro.py "K:\Music" --text "♪"           # custom intro text
```

---

### `embed_lyrics.py`
Embeds the contents of each `.lrc` file into the matching audio file's lyrics tag. For MP3s, automatically selects SYLT (synced) if the LRC contains timestamps, or USLT (plain text) if it does not. Use `--uslt` to force USLT regardless.

| Format | Tag |
|--------|-----|
| MP3 | SYLT (synced) or USLT (plain), auto-detected |
| M4A | `©lyr` (iTunes lyrics field) |
| FLAC | `LYRICS` (Vorbis comment) |

```bash
python embed_lyrics.py "K:\Music"
python embed_lyrics.py                        # prompts for path
python embed_lyrics.py "K:\Music" --overwrite
python embed_lyrics.py "K:\Music" --language fra
python embed_lyrics.py "K:\Music" --uslt      # MP3: always write USLT
```

---

### `strip_lrc_timestamps.py`
Removes LRC timestamps from embedded lyrics tags (USLT, `©lyr`, LYRICS), leaving plain unsynced text. Files with no timestamps in their lyrics tag are skipped.

```bash
python strip_lrc_timestamps.py "K:\Music"
python strip_lrc_timestamps.py                # prompts for path
```

---

### `lrc_offset.py`
Shifts all timestamps in a single `.lrc` file by a fixed number of seconds. Positive values delay the lyrics; negative values advance them. Timestamps that would go below zero are clamped to `[00:00.00]`.

```bash
python lrc_offset.py "Smile.lrc" +2.5
python lrc_offset.py "Smile.lrc" -0.03
python lrc_offset.py                          # prompts for file and offset
```

---

### `export_metadata.py`
Reads every audio file in a folder hierarchy and writes path, artist, album, title, and bitrate to a CSV file.

| Format | Bitrate column |
|--------|---------------|
| MP3 | `320 kbps` |
| M4A | `256 kbps` |
| FLAC | `24bit/96kHz` |

```bash
python export_metadata.py "K:\Music"
python export_metadata.py                          # prompts for path
python export_metadata.py "K:\Music" --output library.csv
```

---

## Shared Module

### `lrc_utils.py`
Common LRC parsing and formatting utilities used by the scripts above. All timestamps are handled internally as centiseconds.

| Symbol | Description |
|--------|-------------|
| `TIMED_RE` | Regex matching a timed LRC line `[mm:ss.cc]` |
| `META_RE` | Regex matching an LRC metadata tag `[ar:...]` etc. |
| `parse_cs(m)` | Convert a `TIMED_RE` match to centiseconds |
| `cs_to_lrc(cs)` | Format centiseconds as `[mm:ss.cc]` |
| `has_timestamps(text)` | Return `True` if text contains any timed lines |
| `strip_timestamps(text)` | Remove timestamps and metadata tags, return plain text |
| `parse_lrc(text)` | Parse LRC into `(lyric, centiseconds)` tuples |

---

## Notes

- All scripts accept the target path as a command-line argument or will prompt if omitted.
- All scripts skip files gracefully and report status per file.
- Permission errors are caught and reported without stopping the run.
- Musixmatch returns 401 errors for unauthenticated requests; `syncedlyrics` falls back to other providers (Lrclib, NetEase, etc.) automatically.
- For Glee Cast covers and other ambiguous tracks, use the full disambiguated title, e.g. `"Smile - Cover of Lily Allen Song"`.
- After updating tags, Navidrome requires a rescan to pick up changes.
