from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

SCRIPT = Path(__file__).parents[2] / "scripts" / "release_audit.py"
SPEC = importlib.util.spec_from_file_location("release_audit", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
release_audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = release_audit
SPEC.loader.exec_module(release_audit)


def test_privacy_scan_detects_media_file_and_serialized_frame(tmp_path: Path) -> None:
    (tmp_path / "capture.jpg").write_bytes(b"not a real image")
    (tmp_path / "messages.jsonl").write_text(
        '{"raw_frame_base64":"data:image/jpeg;base64,abc"}\n', encoding="utf-8"
    )

    findings = release_audit.scan_runtime_privacy([tmp_path], tmp_path)

    assert {finding.rule for finding in findings} == {
        "persisted-media-file",
        "serialized-raw-media",
    }


def test_secret_scan_ignores_blank_examples_and_detects_key(tmp_path: Path) -> None:
    (tmp_path / ".env.example").write_text("OPENAI_API_KEY=\n", encoding="utf-8")
    fake_key = "AKIA" + "ABCDEFGHIJKLMNOP"
    (tmp_path / "leak.txt").write_text(f"token={fake_key}\n", encoding="utf-8")

    findings = release_audit.scan_secrets(tmp_path)

    assert [(finding.rule, finding.path, finding.line) for finding in findings] == [
        ("aws-access-key", "leak.txt", 1)
    ]


def test_run_writes_machine_and_human_readable_evidence(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    output = tmp_path / "evidence"
    repo.mkdir()
    monkeypatch.setattr(
        release_audit,
        "dependency_inventory",
        lambda _root: {"python": [], "npm": []},
    )
    args = release_audit.parse_args(["--repo-root", str(repo), "--output-dir", str(output)])

    assert release_audit.run(args) == 0
    report = json.loads((output / "release-audit.json").read_text(encoding="utf-8"))
    assert report["status"] == "pass"
    assert report["schema_version"] == "1.0"
    assert "Result: **PASS**" in (output / "release-audit.md").read_text(encoding="utf-8")
