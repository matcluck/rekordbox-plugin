#!/usr/bin/env python3
"""Standalone, safety-gated Rekordbox cue publication backend."""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import shutil
import tempfile
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


SEMANTIC_CUE_LABELS = frozenset({
    "First Beat", "Loop In", "Vocal / Buildup", "Drop",
    "Breakdown", "Special", "Outro", "Loop Out",
})


@dataclass(frozen=True)
class RekordboxSourceCue:
    slot: int
    position_ms: int
    comment: str


@dataclass(frozen=True)
class RekordboxCueTransferTrack:
    content_id: str
    media_key: str
    path: str
    duration_ms: int
    cues: tuple[RekordboxSourceCue, ...]


@dataclass
class RekordboxCueTransferPlan:
    plan_path: Path
    tracks: dict[str, RekordboxCueTransferTrack]
    approved_occurrences: int
    unresolved: list[dict]
    uncued: list[dict]

    @property
    def hot_cue_count(self) -> int:
        return sum(len(remap_hot_cues_for_cdj2000(track)) for track in self.tracks.values())

    @property
    def source_cue_count(self) -> int:
        return sum(len(track.cues) for track in self.tracks.values())

    @property
    def memory_cue_count(self) -> int:
        return sum(len({cue.position_ms for cue in track.cues}) for track in self.tracks.values())


def unique_position_cues(track: RekordboxCueTransferTrack) -> list[RekordboxSourceCue]:
    by_position: dict[int, RekordboxSourceCue] = {}
    for cue in sorted(track.cues, key=lambda item: item.slot):
        by_position.setdefault(cue.position_ms, cue)
    return sorted(by_position.values(), key=lambda item: (item.position_ms, item.slot))


def remap_hot_cues_for_cdj2000(track: RekordboxCueTransferTrack) -> list[tuple[int, RekordboxSourceCue]]:
    """Reserve A/B/C for early/middle/late, then place remaining positions D-H."""
    unique = unique_position_cues(track)
    if not unique:
        return []
    selected: dict[int, RekordboxSourceCue] = {0: unique[0]}
    if len(unique) == 2:
        selected[2] = unique[-1]
    elif len(unique) >= 3:
        selected[2] = unique[-1]
        midpoint_ms = track.duration_ms / 2.0 if track.duration_ms > 0 else (unique[0].position_ms + unique[-1].position_ms) / 2.0
        selected[1] = min(unique[1:-1], key=lambda cue: (abs(cue.position_ms - midpoint_ms), cue.position_ms, cue.slot))
    remaining = [cue for cue in unique if cue not in set(selected.values())]
    for target_slot, cue in zip(range(3, 8), remaining, strict=False):
        selected[target_slot] = cue
    if len(selected) != len(unique):
        raise RuntimeError(f"{track.path} has {len(unique)} unique cue positions but only {len(selected)} could be assigned to A-H.")
    return sorted(selected.items())


def memory_cue_rows(track: RekordboxCueTransferTrack) -> list[dict[str, int | str]]:
    unique = unique_position_cues(track)
    if len(unique) > 10:
        raise RuntimeError(f"{track.path} needs {len(unique)} memory cues; CDJ-2000 supports at most 10.")
    return [{"Kind": 0, "InMsec": cue.position_ms, "Comment": cue.comment} for cue in unique]


def previous_cue_rows(track: RekordboxCueTransferTrack) -> list[dict[str, int | str]]:
    rows = [{"Kind": cue.slot + 1, "InMsec": cue.position_ms, "Comment": cue.comment} for cue in track.cues]
    rows.extend(memory_cue_rows(track))
    return rows


def desired_cue_rows(track: RekordboxCueTransferTrack) -> list[dict[str, int | str]]:
    rows = [{"Kind": slot + 1, "InMsec": cue.position_ms, "Comment": cue.comment} for slot, cue in remap_hot_cues_for_cdj2000(track)]
    rows.extend(memory_cue_rows(track))
    return rows


def cue_signature(cues) -> tuple[tuple[int, int, str], ...]:
    return tuple(sorted((int(cue.Kind), int(cue.InMsec), str(cue.Comment or "")) for cue in cues))


def row_signature(rows: list[dict[str, int | str]]) -> tuple[tuple[int, int, str], ...]:
    return tuple(sorted((int(row["Kind"]), int(row["InMsec"]), str(row["Comment"])) for row in rows))


def is_replaceable_analysis_cue(cues) -> bool:
    cues = list(cues)
    return len(cues) == 1 and int(cues[0].Kind) == 1 and str(cues[0].Comment or "").strip().casefold() == "1.1bars" and int(cues[0].OutMsec) == -1


def is_equivalent_previous_transfer(cues, track: RekordboxCueTransferTrack) -> bool:
    cues = list(cues)
    memory = [cue for cue in cues if int(cue.Kind) == 0]
    hot = [cue for cue in cues if int(cue.Kind) > 0]
    desired_positions = {cue.position_ms for cue in unique_position_cues(track)}
    if not desired_positions or not memory or not hot:
        return False
    if any(int(cue.OutMsec) != -1 or int(cue.Kind) not in range(9) or str(cue.Comment or "") not in SEMANTIC_CUE_LABELS for cue in cues):
        return False
    memory_positions = [int(cue.InMsec) for cue in memory]
    hot_positions = {int(cue.InMsec) for cue in hot}
    hot_kinds = [int(cue.Kind) for cue in hot]
    return len(memory_positions) == len(desired_positions) and set(memory_positions) == desired_positions and hot_positions == desired_positions and len(hot_kinds) == len(set(hot_kinds)) and len(hot_kinds) <= 8


def path_key(value: str) -> str:
    return value.replace("\\", "/").rstrip("/").casefold()


def inspect_rekordbox_cue_transfer(plan: RekordboxCueTransferPlan, database: Path) -> dict:
    from pyrekordbox import Rekordbox6Database
    from pyrekordbox.db6 import DjmdContent, DjmdCue
    from sqlalchemy import text

    content_ids = list(plan.tracks)
    with Rekordbox6Database(path=database, db_dir=database.parent) as db:
        contents = {str(content.ID): content for content in db.query(DjmdContent).filter(DjmdContent.ID.in_(content_ids))}
        cues_by_content: dict[str, list] = {content_id: [] for content_id in content_ids}
        for cue in db.query(DjmdCue).filter(DjmdCue.ContentID.in_(content_ids)):
            cues_by_content.setdefault(str(cue.ContentID), []).append(cue)
        actions: dict[str, str] = {}
        details: dict[str, dict] = {}
        for content_id, track in plan.tracks.items():
            content = contents.get(content_id)
            if content is None:
                actions[content_id] = "missing_content"
                details[content_id] = {"path": track.path}
                continue
            rekordbox_path = str(content.FolderPath or "")
            if path_key(rekordbox_path) != path_key(track.path):
                actions[content_id] = "path_mismatch"
                details[content_id] = {"path": track.path, "rekordbox_path": rekordbox_path, "title": str(content.Title or "")}
                continue
            existing = cues_by_content.get(content_id, [])
            if not existing:
                action = "empty"
            elif cue_signature(existing) == row_signature(desired_cue_rows(track)):
                action = "identical"
            elif is_replaceable_analysis_cue(existing):
                action = "replace_analysis"
            elif cue_signature(existing) == row_signature(previous_cue_rows(track)):
                action = "replace_previous_transfer"
            elif is_equivalent_previous_transfer(existing, track):
                action = "replace_equivalent_transfer"
            else:
                action = "conflict"
            actions[content_id] = action
            details[content_id] = {"path": track.path, "title": str(content.Title or ""), "existing_cues": len(existing), "desired_cues": len(desired_cue_rows(track))}
        integrity = str(db.session.connection().execute(text("PRAGMA integrity_check")).scalar())
        foreign_keys = list(db.session.connection().execute(text("PRAGMA foreign_key_check")).fetchall())
    db.engine.dispose()
    action_names = ("empty", "replace_analysis", "replace_previous_transfer", "replace_equivalent_transfer", "identical", "conflict", "missing_content", "path_mismatch")
    return {"actions": actions, "details": details, "counts": {name: sum(value == name for value in actions.values()) for name in action_names}, "integrity": integrity, "foreign_key_errors": len(foreign_keys)}


def new_cue_id(used: set[str]) -> str:
    while True:
        candidate = str(secrets.randbits(32))
        if int(candidate) >= 100 and candidate not in used:
            used.add(candidate)
            return candidate


def apply_rekordbox_cues_to_database(plan: RekordboxCueTransferPlan, database: Path, override_conflicts: frozenset[str] = frozenset()) -> dict:
    from pyrekordbox import Rekordbox6Database
    from pyrekordbox.db6 import DjmdContent, DjmdCue

    inspection = inspect_rekordbox_cue_transfer(plan, database)
    invalid = {content_id: inspection["actions"].get(content_id) for content_id in override_conflicts if inspection["actions"].get(content_id) != "conflict"}
    if invalid:
        detail = ", ".join(f"{content_id}={action or 'not-in-plan'}" for content_id, action in sorted(invalid.items()))
        raise RuntimeError("Conflict overrides must name current protected conflicts: " + detail)
    writable = {content_id for content_id, action in inspection["actions"].items() if action in {"empty", "replace_analysis", "replace_previous_transfer", "replace_equivalent_transfer"} or (action == "conflict" and content_id in override_conflicts)}
    if not writable:
        return {"inserted": 0, "deleted": 0, "updated_tracks": 0}
    inserted = deleted = 0
    with Rekordbox6Database(path=database, db_dir=database.parent) as db:
        contents = {str(content.ID): content for content in db.query(DjmdContent).filter(DjmdContent.ID.in_(writable))}
        existing: dict[str, list] = {content_id: [] for content_id in writable}
        for cue in db.query(DjmdCue).filter(DjmdCue.ContentID.in_(writable)):
            existing.setdefault(str(cue.ContentID), []).append(cue)
        used_ids = {str(row[0]) for row in db.query(DjmdCue.ID).all()}
        now = datetime.now(timezone.utc)
        for content_id in sorted(writable):
            content = contents[content_id]
            for cue in existing.get(content_id, []):
                db.delete(cue)
                deleted += 1
            for values in desired_cue_rows(plan.tracks[content_id]):
                position_ms = int(values["InMsec"])
                db.add(DjmdCue.create(ID=new_cue_id(used_ids), ContentID=content_id, ContentUUID=content.UUID, UUID=str(uuid.uuid4()), InMsec=position_ms, InFrame=position_ms * 150 // 1000, InMpegFrame=0, InMpegAbs=0, OutMsec=-1, OutFrame=0, OutMpegFrame=0, OutMpegAbs=0, Kind=int(values["Kind"]), Color=255, ColorTableIndex=0, ActiveLoop=0, Comment=str(values["Comment"]), BeatLoopSize=0, CueMicrosec=0, InPointSeekInfo=None, OutPointSeekInfo=None, created_at=now, updated_at=now))
                inserted += 1
            if not content.CueUpdated:
                content.CueUpdated = "1"
            if not content.HotCueAutoLoad:
                content.HotCueAutoLoad = "on"
        db.commit()
    db.engine.dispose()
    return {"inserted": inserted, "deleted": deleted, "updated_tracks": len(writable)}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def running_rekordbox_processes() -> list[str]:
    try:
        import psutil
    except ImportError:
        return []
    names = set()
    for process in psutil.process_iter(["name"]):
        try:
            name = str(process.info.get("name") or "")
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            continue
        if "rekordbox" in name.casefold():
            names.add(name)
    return sorted(names, key=str.casefold)


def ensure_rekordbox_is_closed(database: Path) -> None:
    processes = running_rekordbox_processes()
    if processes:
        raise RuntimeError("Close Rekordbox and its tray agent before changing the Collection: " + ", ".join(processes))
    sidecars = [Path(f"{database}{suffix}") for suffix in ("-wal", "-shm", "-journal") if Path(f"{database}{suffix}").exists()]
    if sidecars:
        raise RuntimeError("Rekordbox database sidecars are still present; open and cleanly close Rekordbox first: " + ", ".join(str(path) for path in sidecars))


def backup_collection(database: Path, artifact_root: Path) -> tuple[Path, Path]:
    root = artifact_root / "rekordbox-backups" / (time.strftime("%Y%m%d-%H%M%S") + "-before-cues")
    suffix = 1
    while root.exists():
        root = root.with_name(re.sub(r"-\d+$", "", root.name) + f"-{suffix}")
        suffix += 1
    root.mkdir(parents=True)
    backup = root / database.name
    shutil.copy2(database, backup)
    playlist_xml = database.parent / "masterPlaylists6.xml"
    if playlist_xml.is_file():
        shutil.copy2(playlist_xml, root / playlist_xml.name)
    return root, backup


def verify_result(plan: RekordboxCueTransferPlan, database: Path, initial: dict, overrides: frozenset[str]) -> dict:
    result = inspect_rekordbox_cue_transfer(plan, database)
    if result["integrity"] != "ok" or result["foreign_key_errors"]:
        raise RuntimeError(f"Rekordbox verification failed: integrity={result['integrity']}; foreign keys={result['foreign_key_errors']}")
    expected = sum(initial["counts"][name] for name in ("empty", "replace_analysis", "replace_previous_transfer", "replace_equivalent_transfer", "identical")) + len(overrides)
    if result["counts"]["identical"] != expected:
        raise RuntimeError(f"Rekordbox cue readback mismatch: expected {expected} exact tracks, found {result['counts']['identical']}.")
    for content_id, action in initial["actions"].items():
        if content_id in overrides:
            if action != "conflict" or result["actions"].get(content_id) != "identical":
                raise RuntimeError(f"Overridden Rekordbox content {content_id} did not verify as identical.")
        elif action in {"conflict", "missing_content", "path_mismatch"} and result["actions"].get(content_id) != action:
            raise RuntimeError(f"Protected Rekordbox content {content_id} changed unexpectedly.")
    return result


def apply_rekordbox_cues_to_active_collection(plan: RekordboxCueTransferPlan, database: Path, override_conflicts: frozenset[str] = frozenset()) -> tuple[Path, Path, dict]:
    if not database.is_file():
        raise FileNotFoundError(f"Rekordbox Collection is missing: {database}")
    ensure_rekordbox_is_closed(database)
    initial = inspect_rekordbox_cue_transfer(plan, database)
    invalid = {content_id: initial["actions"].get(content_id) for content_id in override_conflicts if initial["actions"].get(content_id) != "conflict"}
    if invalid:
        raise RuntimeError("Conflict overrides must name current protected conflicts: " + ", ".join(f"{key}={value or 'not-in-plan'}" for key, value in sorted(invalid.items())))
    if initial["integrity"] != "ok" or initial["foreign_key_errors"]:
        raise RuntimeError("The live Rekordbox Collection failed pre-write validation.")
    source_hash = sha256_file(database)
    operation_root, backup = backup_collection(database, plan.plan_path.parent)
    if sha256_file(backup) != source_hash:
        raise RuntimeError("Rekordbox backup hash does not match the live Collection.")
    candidate_dir = Path(tempfile.mkdtemp(prefix=".rekordbox-cues-", dir=database.parent))
    candidate = candidate_dir / database.name
    live_xml = database.parent / "masterPlaylists6.xml"
    candidate_xml = candidate_dir / live_xml.name
    try:
        shutil.copy2(database, candidate)
        if live_xml.is_file():
            shutil.copy2(live_xml, candidate_xml)
        changes = apply_rekordbox_cues_to_database(plan, candidate, override_conflicts)
        verify_result(plan, candidate, initial, override_conflicts)
        ensure_rekordbox_is_closed(database)
        if sha256_file(database) != source_hash:
            raise RuntimeError("The live Rekordbox Collection changed while the candidate was built.")
        os.replace(candidate, database)
        try:
            live_verified = verify_result(plan, database, initial, override_conflicts)
        except Exception:
            shutil.copy2(backup, database)
            raise RuntimeError("Post-install verification failed; the Rekordbox backup was restored.")
    finally:
        for path in (candidate, candidate_xml, Path(f"{candidate}-wal"), Path(f"{candidate}-shm"), Path(f"{candidate}-journal")):
            path.unlink(missing_ok=True)
        try:
            candidate_dir.rmdir()
        except OSError:
            pass
    journal = operation_root / "rekordbox-cue-publication.json"
    journal.write_text(json.dumps({"type": "proposal_to_rekordbox_cues", "created_at": datetime.now(timezone.utc).isoformat(), "plan": str(plan.plan_path), "database": str(database), "backup": str(backup), "database_sha256_before": source_hash, "database_sha256_after": sha256_file(database), "source_tracks": len(plan.tracks), "source_cues": plan.source_cue_count, "output_hot_cues": plan.hot_cue_count, "output_memory_cues": plan.memory_cue_count, "unresolved_occurrences": len(plan.unresolved), "uncued_tracks": plan.uncued, "overridden_conflicts": sorted(override_conflicts), "initial_counts": initial["counts"], "changes": changes, "verified_counts": live_verified["counts"]}, indent=2), encoding="utf-8")
    return backup, journal, live_verified
