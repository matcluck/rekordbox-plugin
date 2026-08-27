#!/usr/bin/env python3
"""Preview or publish a reviewed Music Organiser cue proposal to Rekordbox."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from rekordbox_backend import (
    RekordboxCueTransferPlan,
    RekordboxCueTransferTrack,
    RekordboxSourceCue,
    apply_rekordbox_cues_to_active_collection,
    inspect_rekordbox_cue_transfer,
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def path_key(value: str) -> str:
    return value.replace("\\", "/").rstrip("/").casefold()


def build_plan(payload: dict, proposal_path: Path, database: Path):
    if payload.get("schema") != "music-organiser.cue-proposal/v1":
        raise RuntimeError("Unsupported cue proposal schema.")
    from pyrekordbox import Rekordbox6Database
    from pyrekordbox.db6 import DjmdContent

    contents = {}
    with Rekordbox6Database(path=database, db_dir=database.parent) as db:
        for row in db.query(DjmdContent):
            key = path_key(str(row.FolderPath or ""))
            if key in contents:
                contents[key] = None
            else:
                contents[key] = str(row.ID)
    db.engine.dispose()
    tracks = {}
    unresolved = []
    for item in payload.get("tracks", []):
        source = Path(item["path"]).resolve()
        if item.get("analysis_failure"):
            unresolved.append({"path": str(source), "reason": item["analysis_failure"]})
            continue
        if not source.is_file() or source.stat().st_size != int(item["bytes"]) or sha256(source) != item["sha256"]:
            raise RuntimeError(f"Proposal source identity changed: {source}")
        duration_ms = int(item["duration_ms"])
        cues = []
        slots = set()
        for cue in item.get("cues", []):
            slot = int(cue["slot"])
            position = int(cue["position_ms"])
            if slot not in range(8) or slot in slots or position < 0 or position > duration_ms:
                raise RuntimeError(f"Invalid or duplicate cue in proposal: {source}")
            slots.add(slot)
            cues.append(RekordboxSourceCue(slot, position, str(cue["label"])[:255]))
        content_id = contents.get(path_key(str(source)))
        if content_id is None:
            reason = "path is missing or ambiguous in Rekordbox"
            unresolved.append({"path": str(source), "reason": reason})
            continue
        tracks[content_id] = RekordboxCueTransferTrack(content_id, "proposal:" + item["sha256"], str(source), duration_ms, tuple(cues))
    return RekordboxCueTransferPlan(proposal_path, tracks, len(payload.get("tracks", [])), unresolved, [])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("proposal", type=Path)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--approve-proposal", action="store_true", help="Confirm the reviewed proposal is approved for this publication")
    parser.add_argument("--allow-unresolved", action="store_true", help="Apply resolved tracks even when separately reported proposal tracks are unresolved")
    parser.add_argument("--override-conflict", action="append", default=[])
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    proposal = args.proposal.resolve()
    database = args.database.resolve()
    payload = json.loads(proposal.read_text(encoding="utf-8"))
    plan = build_plan(payload, proposal, database)
    inspection = inspect_rekordbox_cue_transfer(plan, database)
    print(json.dumps({"operation_id": payload.get("operation_id"), "tracks": len(plan.tracks), "unresolved": plan.unresolved, "counts": inspection["counts"], "integrity": inspection["integrity"], "foreign_key_errors": inspection["foreign_key_errors"]}, indent=2))
    if not args.apply:
        print("Dry run only. No Rekordbox data changed.")
        return 0
    if not args.approve_proposal:
        raise RuntimeError("--apply requires --approve-proposal after reviewing this exact artifact.")
    if plan.unresolved and not args.allow_unresolved:
        raise RuntimeError("The proposal has unresolved tracks; review them or explicitly pass --allow-unresolved.")
    overrides = frozenset(str(value) for value in args.override_conflict)
    backup, journal, verified = apply_rekordbox_cues_to_active_collection(plan, database, overrides)
    journal_payload = json.loads(journal.read_text(encoding="utf-8"))
    journal_payload.update({"type": "proposal_to_rekordbox_cues", "proposal": str(proposal), "operation_id": payload.get("operation_id")})
    journal.write_text(json.dumps(journal_payload, indent=2) + "\n", encoding="utf-8")
    print(f"Backup: {backup}\nJournal: {journal}\nVerified: {verified['counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
