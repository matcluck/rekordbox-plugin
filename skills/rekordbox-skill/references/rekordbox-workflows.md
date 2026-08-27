# Rekordbox workflows

Use the standalone backend bundled with this skill and run it through the skill's locked project environment. Do not resolve or load a djay workspace for ordinary Rekordbox work.

## Collection and playlist inspection

```text
playlists rekordbox --flat
playlist show rekordbox <name-or-id>
playlist create rekordbox <name> [--folder] [--parent REF] [--apply]
playlist rename rekordbox <ref> <new-name> [--apply]
playlist delete rekordbox <ref> [--recursive] [--apply]
```

Use stable IDs or full paths when names are ambiguous. Playlist deletion removes playlist records and memberships only, never audio.

## Cue publication

The proven legacy transfer is:

```text
rekordbox cues [plan.csv]
rekordbox cues [plan.csv] --apply
```

It reads cue data from djay and must therefore be labeled `cue_source=djay`. Preserve non-generated Rekordbox cues as conflicts. An approved override must identify the exact current content ID and fail closed if the conflict classification changes.

The destination-neutral direct interface consumes a reviewed proposal artifact with, at minimum:

- schema version and operation ID;
- canonical audio path, size, duration, and full hash;
- analysis engine and model revision;
- cue slot, semantic label, and millisecond position;
- source-grid or snapping evidence;
- per-track review and publication approval.

Validate source identity and timestamps before converting proposals into `djmdCue` rows. For original CDJ-2000 compatibility, deduplicate positions, map earliest/middle/latest to A/B/C, place remaining positions in D-H chronologically, and mirror distinct positions into memory cues. Refuse more than ten unique memory positions.

```text
python scripts/publish_cue_proposals.py proposal.json --database <master.db>
python scripts/publish_cue_proposals.py proposal.json --database <master.db> --approve-proposal --apply
```

The first form is read-only. The apply form reuses the maintained backend's process-closure, conflict, backup, copied-database, atomic-install, rollback, and read-back gates and writes a proposal-specific journal type.

## Optional import from djay

Only load `djay-skill` and [rekordbox-cue-transfer.md](rekordbox-cue-transfer.md) when the user explicitly requests existing djay cues as the source. That adapter may accept a djay workspace or database supplied by the djay skill. It is not part of Rekordbox dependency setup and must never become a fallback for `cue_source=proposal` or `rekordbox-native`.

## Exact track removal

Preview `rekordbox remove <exact-audio-path-or-content-id>` before `--apply`. Require Rekordbox and the tray agent to be closed. Back up `master.db` and `masterPlaylists6.xml`, enumerate every directly referenced row, validate a copied database, then install atomically and verify managed analysis/artwork cleanup.

## Native playlists and devices

- Publish only non-empty, performance-ready playlists explicitly approved by name.
- Keep review, WIP, optional, acquisition, and confidence-tier crates in evidence files unless the user explicitly requests that native crate.
- Use Rekordbox Export mode, its device tree, or Sync Manager for final media publication.
- Confirm exact CDJ model, filesystem, codec support, capacity, file-count headroom, and existing device contents before proposing replacement.
- After export, wait for confirmation that Rekordbox is closed and the device is safely ejected before verification.
