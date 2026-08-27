---
name: rekordbox-skill
description: Safely inspect and update Rekordbox collections, playlists, cue points, analysis state, and Pioneer CDJ exports. Use for encrypted master.db work, pyrekordbox operations, native playlist publication, cue mapping, exact track removal, Rekordbox USB or SD preparation, or publishing approved cue proposals into Rekordbox. Do not use for djay database writes.
---

# Rekordbox

Treat Rekordbox as an independent publication target. Do not require djay unless the user explicitly chooses djay as the cue source.

## Boundaries

- Use `music-organiser` for source inventory, metadata inference, audio organization, deduplication, and destination-neutral cue proposals.
- Use this skill for local Rekordbox Collection records, playlists, cues, analysis state, and native device exports.
- Use `djay-skill` only for djay-specific work or when the user explicitly selects existing djay cues as the source.
- For an end-to-end request, return verified Rekordbox results and journals to `music-organiser`; never mutate djay as an incidental step.

## Start safely

1. Resolve the active Rekordbox database, version, tray processes, and any removable-device path on every run.
2. Read [references/dependencies.md](references/dependencies.md) before installing or repairing dependencies. Run its read-only preflight first.
3. Read [references/rekordbox-workflows.md](references/rekordbox-workflows.md) before Collection, playlist, cue, or device work.
4. Default to inventory or preview. Do not access `master.db` while Rekordbox is writing, syncing, analyzing, or exporting.
5. Before an approved Collection write, require Rekordbox and its tray agent to be closed, back up the encrypted database and playlist XML together, validate a copied database, apply atomically, and read back the installed result.

Load deeper references only for the matching task:

- Only when the user explicitly requests existing djay cues as input: load `djay-skill`, then read [references/rekordbox-cue-transfer.md](references/rekordbox-cue-transfer.md)
- Original CDJ compatibility, native playlists, and device exports: [references/rekordbox-cdj-workflow.md](references/rekordbox-cdj-workflow.md)

## Cue sources

Keep these modes explicit in every plan and journal:

- `proposal`: cue analysis came from `music-organiser`; preview and publish it directly with `scripts/publish_cue_proposals.py`.
- `djay`: copy existing cues from djay through the proven transfer path after loading `djay-skill` for source inspection.
- `rekordbox-native`: retain or use Rekordbox's own analysis/cues without custom cue generation.

Do not silently substitute `djay` when `proposal` was requested. The direct publisher validates source hashes and cue bounds, then delegates conflict classification, copied-database validation, backup, atomic installation, and read-back to the maintained Rekordbox backend.

## Core safeguards

- Preserve custom Rekordbox cues as conflicts unless the user approves the exact current conflict.
- Do not modify beat grids or managed analysis files merely to publish cue points.
- Treat native Collection approval and removable-device replacement approval as separate decisions.
- Use Rekordbox's native export workflow for final device publication; a raw file copy is not a valid Pioneer export.
- Never inspect or write a device while Rekordbox is exporting to it. Verify only after Rekordbox is closed and the device is safely ejected.
- Preserve playlists the user deleted; do not recreate them without fresh approval.

## Invocation

- Codex marketplace plugin: `$rekordbox-skill:rekordbox-skill`
- Claude Code marketplace plugin: `/rekordbox-skill:rekordbox-skill`
- Direct standalone skill install: `$rekordbox-skill` in Codex or `/rekordbox-skill` in Claude Code

The same `SKILL.md` supplies both interfaces; do not maintain a duplicate slash-command body.

## Finish

Report the Collection and backup paths, operation journal, integrity and foreign-key results, affected content and cue counts, conflicts, device state, and shortest safe next action. State which cue-source mode was used.

## Bundled tool

- `scripts/dependency_preflight.ps1`: read-only checks for the standalone project-local Rekordbox runtime; add `-Install` only after approval for scoped dependency setup.
- `scripts/rekordbox_backend.py`: bundled Rekordbox-only cue mapping, conflict inspection, copied-database mutation, backup, atomic installation, rollback, and read-back. It never imports djay.
- `scripts/publish_cue_proposals.py`: direct destination-neutral proposal preview/publication. `--apply` additionally requires `--approve-proposal`; it never reads a djay database.
- `scripts/stage_rekordbox_usb.ps1`: dry-run-first, hash-verified staging of audio payloads from an existing Rekordbox device. It never manufactures a Pioneer export database and is not a substitute for Rekordbox's native export workflow.
