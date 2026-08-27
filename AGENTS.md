# Rekordbox skill repository

- Treat `skills/rekordbox-skill/SKILL.md` as the canonical cross-runtime skill.
- Resolve Rekordbox databases, exports, devices, backups, and audio roots at runtime. Never embed contributor paths, hostnames, private IPs, personal library counts, or track names.
- Keep Rekordbox Collection, playlist, cue, analysis-state, and Pioneer-device behavior here.
- Keep music metadata and cue-generation policy in `music-organiser`; keep djay writes in `djay-skill`.
- Default to read-only inspection or dry-run. Never write `master.db` while Rekordbox or its tray agent is running.
- Treat native Collection approval and device replacement approval as separate decisions.
- Run self-contained tests and the public-safety scan before handoff, then validate with the bundled `skill-creator` validator.
- Do not commit unless the user explicitly asks.
