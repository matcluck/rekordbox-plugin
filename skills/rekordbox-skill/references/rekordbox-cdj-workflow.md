# Rekordbox and Legacy CDJ Workflow

Use this reference for Rekordbox collections and Pioneer USB/SD exports, especially original CDJ-2000-era devices.

## Safety Gate

- Inventory first. Never write Rekordbox, audio, or a device during research.
- Store reports, plans, review files, and database backups outside audio roots and removable media.
- Do not write `master.db` while Rekordbox is running. Ask the user to save and close it; never terminate the app.
- While Rekordbox is exporting, syncing, analyzing, or writing a device, treat both `master.db` and the device as locked. Do not inspect, verify, or modify either until Rekordbox is closed and the device is safely ejected.
- Before any playlist write, back up `master.db`, `master.db-wal`, `master.db-shm`, and `masterPlaylists6.xml` if present. Validate the intended operation on a copied database first.
- Do not clear, format, or replace a device export without explicit user approval. A full device can contain the only copy of an old export.
- Native-playlist approval does not authorize replacing a USB/SD export. Device-replacement approval does not authorize changing the live Rekordbox collection.
- Do not delete audio to make a device fit. Build a selection plan instead.

## Device Constraints

- Confirm the exact CDJ model before committing to formats or limits. Older Pioneer players commonly require FAT32/MBR media and have lower practical file-count limits.
- For the original CDJ-2000, target fewer than 10,000 unique audio files; leave headroom for Rekordbox analysis, artwork, filesystem allocation, and future additions.
- Verify selected audio codecs, not merely file extensions. In particular, an `.m4a` must be AAC when the device does not support ALAC.
- Use Rekordbox's own export/device workflow for the final device. A raw file copy does not create the Pioneer database, waveforms, cues, and playlist structure required by CDJs.

## Evidence-Backed Curation

1. Build a read-only inventory: content ID, title, artist, version text, genre, duration, codec, size, source path, playlists, cue/analysis state, ratings, play history, and release-year reliability.
2. Inspect the device separately: free space, filesystem, partition scheme, existing `PIONEER` database, audio count, and analysis/artwork footprint.
3. Treat missing ratings, play counts, or playlists as missing evidence, not popularity evidence.
4. Research crowd recognition with appropriate sources. For Australian party music, use official ARIA annual charts and the official triple j Hottest 100 archive as primary signals. Use other chart sources only as documented secondary evidence.
5. Require a normalized title and artist match. Never promote a track from a title-only chart match.
6. Preserve versions. Prefer one normal, high-quality version for the main crowd crate. Keep remixes, mashups, edits, bootlegs, acapellas, and instrumentals in review manifests unless the version itself has evidence or the user explicitly wants a live DJ-tools crate.
7. Use genre metadata for supplementary personal crates only; do not portray every tagged genre track as crowd-proven. Do not invent narrow subgenres from unreliable tags.
8. Generate a reviewable CSV containing source evidence, confidence, version status, proposed playlist, codec, bytes, and absolute source path.

## DJ-Facing Playlist Design

Name playlists for an in-set decision, not for a research score. Define the final root from the user-approved event brief and keep its literal names in ignored run evidence. A practical structure can contain:

- one performance-tools playlist;
- one broad crowd-recognition playlist;
- user-approved genre browse playlists; and
- optional era browse playlists.

Merge invisible research tiers into a clear crowd crate. Keep decade lists as overlapping browse paths. Apply the user's event brief before using any default layout.

Do not create empty playlists. Keep research, review, acquisition, confidence, and other planning-state playlists in private run evidence unless the user explicitly approves an individual playlist for live use. Do not place their literal names in public documentation.

## Publication Gate

Classify every proposed playlist before a native write:

- `performance-final`: eligible for live Rekordbox only after explicit user approval.
- `review-only`: CSV/Markdown evidence; never native by default.
- `optional-library`: evidence only until the user explicitly asks to browse it in Rekordbox.
- `acquisition/wishlist`: evidence only; never create an empty or placeholder native playlist.

The playlist manifest should include `native_apply`, `default_usb`, `status`, and `approval_basis`. Default `native_apply` to `no`. Set it to `yes` only for non-empty `performance-final` playlists covered by the user's approval. Present final names and counts before applying when the approval scope is not already exact.

Treat a user's deletion of a generated playlist as a deliberate curation decision. Record it in the next manifest and do not recreate the playlist without fresh explicit approval.

## Native Rekordbox Playlists

1. Produce a no-write playlist manifest first, using Rekordbox content IDs rather than filenames and applying the publication gate.
2. Exclude every `native_apply = no` playlist from the live migration, even if it is useful to research or a possible future USB.
3. With Rekordbox closed, validate only the approved final set: creation, song membership, reopening, and `PRAGMA integrity_check` on a copied database.
4. Back up the live database, apply native playlist changes transactionally, reopen it, verify counts and integrity, then launch Rekordbox for the user to inspect.
5. Preserve unrelated user playlists. If replacing a generated tree, create and verify the replacement before removing only the generated tree.
6. After inspection, respect any playlists the user removes. Do not repair them merely because they remain in an older plan.

## Native Device Export

Use Rekordbox's native Export mode, device tree, or Sync Manager for the actual export. Do not manufacture Pioneer device databases or use a raw file copy as the final export.

During export, do not inspect the device or `master.db`. After the user confirms the transfer finished, Rekordbox is closed, and the device is safely ejected, verify the device has:

- the explicitly selected performance playlists;
- fewer than the model's supported/practical file count;
- expected audio bytes plus realistic analysis/artwork overhead;
- a populated Pioneer export database; and
- only source files whose codecs the device supports.

Report what was exported, what was intentionally excluded, and where the database backup and selection manifest live.
