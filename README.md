# Rekordbox plugin

The Rekordbox plugin safely inspects and updates Rekordbox collections, playlists, cue points, analysis state, and Pioneer-compatible exports. It is a standalone destination for Claude Code and Codex: Music Organiser can publish directly to Rekordbox without passing through djay.

## Install from the DJ Tools marketplace

### Claude Code

```text
/plugin marketplace add matcluck/dj-tools-marketplace
/plugin install rekordbox-skill@dj-tools
```

### Codex

```text
codex plugin marketplace add matcluck/dj-tools-marketplace
codex plugin add rekordbox-skill@dj-tools
```

## Invocation

| Runtime | Command |
| --- | --- |
| Codex | `$rekordbox-skill:rekordbox-skill` |
| Claude Code | `/rekordbox-skill:rekordbox-skill` |

The canonical instructions are in [`skills/rekordbox-skill/SKILL.md`](skills/rekordbox-skill/SKILL.md). Run the read-only dependency preflight before accessing a collection:

```powershell
.\skills\rekordbox-skill\scripts\dependency_preflight.ps1
```

Collection writes require Rekordbox and its tray agent to be closed, a validated backup and staged candidate, integrity checks, atomic installation, and read-back. Device replacement is a separate approval from Collection publication.

`skills/rekordbox-skill/scripts/publish_cue_proposals.py` publishes Music Organiser's reviewed, hash-bound cue artifact directly to Rekordbox. It does not register or analyse the track in djay first.

The normal runtime is self-contained under `skills/rekordbox-skill`: `pyproject.toml`, `uv.lock`, and `scripts/rekordbox_backend.py`. No djay workspace, djay database, or external djay script is needed. Existing djay cues remain available only when the user explicitly selects djay as the source.

## Local validation

```powershell
claude plugin validate .
python -m unittest discover -s '.\skills\rekordbox-skill\tests' -p 'test_*.py'
```

## Upstream work and acknowledgements

- [`dylanljones/pyrekordbox`](https://github.com/dylanljones/pyrekordbox) (MIT) provides the independent Python interface used by the maintained backend for Rekordbox databases and related formats.
- [`mcroydon/djcues`](https://github.com/mcroydon/djcues) (BSD-3-Clause) is relevant prior art for phrase-aware hot-cue and memory-cue placement and the standardized A-H cue layout.
- [`payne0420/djay-pro-autohotcue`](https://github.com/payne0420/djay-pro-autohotcue) (MIT) is the source of the legacy djay cue-analysis route when the user explicitly chooses djay as the cue source.

See the upstream repositories for complete copyright and license notices. This project is independent community tooling and is not affiliated with AlphaTheta or Pioneer DJ.

## Public-data boundary

The repository contains no Rekordbox collection, encryption material, device export, music, credentials, machine-specific run records, or personal paths. Local artifacts belong in ignored directories. Public-safety tests enforce that boundary.
