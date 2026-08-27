import re
import importlib.util
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = ROOT.parents[1]


def publishable_files():
    result = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=REPOSITORY_ROOT, check=True, capture_output=True, text=True)
    return [REPOSITORY_ROOT / line for line in result.stdout.splitlines() if line and (REPOSITORY_ROOT / line).is_file()]


class RekordboxSkillTests(unittest.TestCase):
    def test_publishable_text_has_no_private_machine_data(self):
        markers = ["/Users" + "/", "/home" + "/"]
        drive_path = re.compile(r"\b[A-Za-z]:\\")
        private_ip = re.compile(r"\b(?:10\.|192\.168\.|172\.(?:1[6-9]|2\d|3[01])\.)\d{1,3}(?:\.\d{1,3}){2}\b")
        email = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
        secret = re.compile(r"\b(?:api[_-]?key|password|secret|access[_-]?token)\s*[:=]\s*['\"][^<'\"]+", re.I)
        failures = []
        for path in publishable_files():
            text = path.read_text(encoding="utf-8")
            if any(marker.casefold() in text.casefold() for marker in markers) or drive_path.search(text) or private_ip.search(text) or email.search(text) or secret.search(text):
                failures.append(str(path.relative_to(REPOSITORY_ROOT)))
        self.assertEqual(failures, [])

    def test_usb_staging_dry_run_and_verified_copy(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            payload = base / "source" / "Contents"
            payload.mkdir(parents=True)
            fixture = payload / "cc0-generated-tone.wav"
            with wave.open(str(fixture), "wb") as audio:
                audio.setnchannels(1)
                audio.setsampwidth(2)
                audio.setframerate(8000)
                audio.writeframes(b"\x00\x00" * 800)
            staging = base / "staging"
            command = ["powershell", "-NoProfile", "-File", str(ROOT / "scripts" / "stage_rekordbox_usb.ps1"), "-SourceRoot", str(base / "source"), "-StagingRoot", str(staging)]
            dry_run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(dry_run.returncode, 0, dry_run.stderr)
            self.assertFalse(staging.exists())
            applied = subprocess.run(command + ["-Apply"], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(applied.returncode, 0, applied.stderr)
            copied_files = list(staging.rglob(fixture.name))
            self.assertEqual(len(copied_files), 1)
            copied = copied_files[0]
            self.assertEqual(copied.read_bytes(), fixture.read_bytes())

    def test_direct_proposal_publisher_has_a_standalone_cli(self):
        completed = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "publish_cue_proposals.py"), "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("--approve-proposal", completed.stdout)
        self.assertNotIn("--backend", completed.stdout)

    def test_standalone_backend_maps_early_middle_late(self):
        path = ROOT / "scripts" / "rekordbox_backend.py"
        spec = importlib.util.spec_from_file_location("standalone_rekordbox_backend", path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        cues = tuple(module.RekordboxSourceCue(index, position, f"Fixture {index}") for index, position in enumerate((1000, 2000, 5500, 9000)))
        track = module.RekordboxCueTransferTrack("1", "proposal:fixture", "fixture.wav", 10000, cues)
        mapped = module.remap_hot_cues_for_cdj2000(track)
        self.assertEqual([(slot, cue.position_ms) for slot, cue in mapped], [(0, 1000), (1, 5500), (2, 9000), (3, 2000)])


if __name__ == "__main__":
    unittest.main()
