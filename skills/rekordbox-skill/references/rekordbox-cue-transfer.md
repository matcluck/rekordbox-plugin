# djay to local Rekordbox cue transfer

> This is the proven `cue_source=djay` adapter. It does not define the destination-neutral `cue_source=proposal` publisher owned by the new split architecture.

## Contents

- [Purpose and scope](#purpose-and-scope)
- [Observed Rekordbox schema](#observed-rekordbox-schema)
- [CDJ-2000 mapping](#cdj-2000-mapping)
- [Conflict policy](#conflict-policy)
- [Repeatable workflow](#repeatable-workflow)
- [Verified result](#verified-result)

## Purpose and scope

Copy already-generated djay cue points into the encrypted local Rekordbox Collection without re-analyzing audio, changing beat grids, writing a USB device, or changing the djay source cue layout.

djay's A-H slots represent semantic categories such as first beat, loop, build, drop, breakdown, special, outro, and loop out. Sparse patterns such as A/B/F/G are valid in djay and do not mean cue data is missing. Apply the early/middle/late remap only to Rekordbox, where it compensates for the original CDJ-2000's three-hotcue limit.

Default paths:

- djay DB: `<workspace>\djay Media Library\MediaLibrary.db`
- Rekordbox DB: `%APPDATA%\Pioneer\rekordbox\master.db`
- approved source mapping: an explicitly supplied, reviewed mapping CSV outside the public skill repository

The workspace project pins `pyrekordbox==0.4.4`, which uses SQLCipher to open Rekordbox 6/7 `master.db`. Run through the workspace environment with `uv run`.

## Observed Rekordbox schema

Rekordbox 7.2.16 stores local cues in `djmdCue`.

| Field | Cue-transfer value |
|---|---|
| `ID` | unused random 32-bit decimal string |
| `ContentID` | exact `djmdContent.ID` from the approved plan |
| `ContentUUID` | matching `djmdContent.UUID` |
| `UUID` | new UUID v4 |
| `InMsec` | rounded djay cue seconds × 1000 |
| `InFrame` | floor(`InMsec × 150 / 1000`) |
| `InMpegFrame`, `InMpegAbs` | `0` |
| `OutMsec` | `-1` for a non-loop cue |
| `OutFrame`, `OutMpegFrame`, `OutMpegAbs` | `0` |
| `Kind` | `0` memory cue; `1`–`8` hot cues A–H |
| `Color` | `255` |
| `ColorTableIndex`, `ActiveLoop`, `BeatLoopSize`, `CueMicrosec` | `0` |
| `Comment` | djay cue label, truncated to 255 characters |

Use pyrekordbox's change registry and commit path so row and global local-USN values advance. Set a previously empty content row's `CueUpdated` to `1` and `HotCueAutoLoad` to `on`.

## CDJ-2000 mapping

The original CDJ-2000 exposes hot cues A-C and supports up to 10 memory cue/loop points per track. Newer CDJ-2000 variants can expose more hot-cue slots.

For every source track:

1. Deduplicate source cues by millisecond position. When several source slots share a timestamp, retain the label from the lowest source slot as the representative.
2. With one distinct position, write it to A. With two, write the earliest to A and the latest to C.
3. With three or more positions, write the earliest to A, the latest to C, and the interior cue nearest 50% of the track duration to B. If duration is unavailable, use the midpoint between the first and last cue; ties prefer the earlier position.
4. Put the remaining distinct positions into D-H in chronological order.
5. Mirror every distinct position as a memory cue with `Kind=0`.
6. Refuse a track requiring more than 10 unique memory positions.

This makes A/B/C useful across the beginning, middle, and end of the track on an original CDJ-2000. Every distinct source position remains reachable through CUE/LOOP CALL, while D-H retain additional direct access on newer players. Duplicate source slots at the same millisecond are deliberately collapsed; no musical position is lost.

## Conflict policy

Classify each exact Rekordbox content ID before writing:

- `empty`: add the desired set.
- `identical`: skip.
- `replace_analysis`: replace only the exact generated singleton pattern `Kind=1`, `Comment=1.1Bars`, `OutMsec=-1`.
- `replace_previous_transfer`: replace the exact older slot-preserving cue set produced by this tool.
- `replace_equivalent_transfer`: replace an older generated set only when its distinct positions still exactly match the current source, its hot-cue kinds are valid and unique, it has no loops, and all labels are known auto-hotcue semantic labels. This safely handles a source duplicate slot that was later removed.
- `conflict`: preserve any other existing cue set and report it.
- `missing_content` or `path_mismatch`: skip and report.

Do not silently overwrite custom Rekordbox cues. Do not modify Rekordbox beat grids or analysis files.

When the user explicitly approves one exact current conflict, pass its Rekordbox
content ID with `--override-conflict <content-id>`. The command must confirm the
ID is still classified as `conflict`, show the authorized title in the preview,
record the override in the journal, and retain the normal backup, copied-database,
integrity, foreign-key, atomic-install, and read-back checks.

## Repeatable workflow

From the workspace:

```powershell
uv sync --locked
uv run python djay.py rekordbox cues
```

Review source counts, unresolved rows, uncued tracks, replacement counts, and conflicts. Then close Rekordbox and its tray agent:

```powershell
uv run python djay.py rekordbox cues --apply
```

For an explicitly approved conflict:

```powershell
uv run python djay.py rekordbox cues --override-conflict <content-id> --apply
```

The apply path must:

1. refuse running Rekordbox processes or live SQLite sidecars;
2. validate integrity and foreign keys;
3. hash and copy the encrypted DB plus `masterPlaylists6.xml` into a timestamped backup;
4. build and commit into a copied DB;
5. reopen the copy and verify every expected cue signature;
6. prove the live DB hash did not change during staging;
7. atomically replace the live DB;
8. reopen and verify the installed DB;
9. restore the backup automatically if post-install verification fails;
10. write `rekordbox-cue-transfer.json` beside the backup.

The command supports `--rekordbox-db <master.db>` for copied-database testing. Never point it at a USB/device database for this local-Collection workflow.

Afterward, open Rekordbox and visually inspect a known track before exporting through Rekordbox's normal device workflow.

## Required verification result

A successful run must report the current source, remapped hot-cue, memory-cue,
replacement, conflict, missing-content, and path-mismatch counts without copying
those library-specific values into this repository. Reopen the encrypted
database, require `PRAGMA integrity_check` and foreign-key checks to pass, and
verify every intended cue signature. Keep the timestamped backup path, journal,
track names, playlist names, and unresolved occurrences in ignored run evidence.
