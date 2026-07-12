#!/usr/bin/env python3
"""Generate repeatable Milestone 5 privacy, secret, and dependency evidence.

The audit is intentionally dependency-free so it can run on the prepared demo
laptop without downloading another scanner. It complements (rather than
replaces) the live offline and usability checklists.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

IGNORED_DIRECTORIES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "node_modules",
}
MEDIA_SUFFIXES = {
    ".avi",
    ".bmp",
    ".gif",
    ".heic",
    ".jpeg",
    ".jpg",
    ".mkv",
    ".mov",
    ".mp4",
    ".png",
    ".webm",
}
SECRET_RULES = {
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "aws-access-key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "github-token": re.compile(r"\bgh[oprsu]_[A-Za-z0-9_]{30,}\b"),
    "openai-key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    "google-api-key": re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
}
RAW_MEDIA_TEXT = re.compile(
    r"(?:data:image/|data:video/|(?:raw_)?(?:frame|image|video)(?:_data|_bytes|_base64)\s*[=:])",
    re.IGNORECASE,
)
TEXT_SUFFIXES = {
    ".conf",
    ".csv",
    ".env",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".jsonl",
    ".log",
    ".md",
    ".py",
    ".sh",
    ".sql",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}


@dataclass(frozen=True)
class Finding:
    audit: str
    rule: str
    path: str
    line: int | None = None


def _files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    if not root.exists():
        return []
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and not any(part in IGNORED_DIRECTORIES for part in path.parts)
    )


def _display(path: Path, base: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def scan_secrets(repo_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for path in _files(repo_root):
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name != ".env":
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for number, line in enumerate(lines, start=1):
            for rule, pattern in SECRET_RULES.items():
                if pattern.search(line):
                    findings.append(Finding("secrets", rule, _display(path, repo_root), number))
    return findings


def scan_runtime_privacy(paths: list[Path], repo_root: Path) -> list[Finding]:
    """Find raw media files or serialized raw-media payloads in runtime artifacts."""

    findings: list[Finding] = []
    for root in paths:
        for path in _files(root):
            display = _display(path, repo_root)
            if path.suffix.lower() in MEDIA_SUFFIXES:
                findings.append(Finding("privacy", "persisted-media-file", display))
                continue
            if path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeDecodeError):
                continue
            for number, line in enumerate(lines, start=1):
                if RAW_MEDIA_TEXT.search(line):
                    findings.append(Finding("privacy", "serialized-raw-media", display, number))
    return findings


def scan_database(database_url: str, repo_root: Path) -> list[Finding]:
    """Scan persisted JSON/text fields for image/video data markers."""

    try:
        import psycopg
    except ImportError as exc:  # pragma: no cover - exercised in prepared runtime
        raise RuntimeError("database audit requires psycopg") from exc

    normalized = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    queries = {
        "events.evidence": "SELECT id, evidence::text FROM events WHERE evidence IS NOT NULL",
        "feedback.payload": "SELECT id, payload::text FROM feedback WHERE payload IS NOT NULL",
        "feedback.detail": "SELECT id, detail FROM feedback WHERE detail IS NOT NULL",
    }
    findings: list[Finding] = []
    with (
        psycopg.connect(normalized, connect_timeout=3) as connection,
        connection.cursor() as cursor,
    ):
        for location, query in queries.items():
            cursor.execute(query)
            for record_id, value in cursor.fetchall():
                if value and RAW_MEDIA_TEXT.search(str(value)):
                    findings.append(
                        Finding(
                            "privacy",
                            "database-raw-media",
                            f"postgresql:{location}:id={record_id}",
                        )
                    )
    return findings


def dependency_inventory(repo_root: Path) -> dict[str, Any]:
    python_packages: list[dict[str, str]] = []
    for distribution in importlib.metadata.distributions():
        metadata = distribution.metadata
        name = metadata.get("Name") or "unknown"
        license_name = metadata.get("License-Expression") or metadata.get("License") or ""
        if not license_name:
            classifiers = metadata.get_all("Classifier", [])
            license_name = ", ".join(
                value.removeprefix("License :: ")
                for value in classifiers
                if value.startswith("License :: ")
            )
        python_packages.append(
            {"name": name, "version": distribution.version, "license": license_name or "UNKNOWN"}
        )
    python_packages.sort(key=lambda item: item["name"].lower())

    npm_packages: list[dict[str, str]] = []
    lock_path = repo_root / "dashboard" / "package-lock.json"
    if lock_path.exists():
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        for location, package in lock.get("packages", {}).items():
            if not location or not isinstance(package, dict):
                continue
            npm_packages.append(
                {
                    "name": location.rsplit("node_modules/", 1)[-1],
                    "version": str(package.get("version", "UNKNOWN")),
                    "license": str(package.get("license", "UNKNOWN")),
                }
            )
        npm_packages.sort(key=lambda item: item["name"].lower())
    return {"python": python_packages, "npm": npm_packages}


def _git_commit(repo_root: Path) -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Milestone 5 Release Audit",
        "",
        f"- Generated (UTC): `{report['generated_at']}`",
        f"- Git commit: `{report['git_commit']}`",
        f"- Result: **{report['status'].upper()}**",
        f"- Findings: `{len(report['findings'])}`",
        f"- Python dependencies: `{len(report['dependencies']['python'])}`",
        f"- npm dependencies: `{len(report['dependencies']['npm'])}`",
        "",
        "## Findings",
        "",
    ]
    if not report["findings"]:
        lines.append("No secret or raw-media persistence findings were detected.")
    else:
        lines.extend(["| Audit | Rule | Location |", "|---|---|---|"])
        for finding in report["findings"]:
            location = finding["path"]
            if finding["line"] is not None:
                location += f":{finding['line']}"
            lines.append(f"| {finding['audit']} | {finding['rule']} | `{location}` |")
    lines.extend(
        [
            "",
            "## Scope note",
            "",
            "A passing automated scan is evidence for the inspected paths/database only. "
            "Complete the offline, webcam, and usability checklists on the target laptop.",
            "",
        ]
    )
    return "\n".join(lines)


def run(args: argparse.Namespace) -> int:
    repo_root = args.repo_root.resolve()
    findings = scan_secrets(repo_root)
    runtime_paths = [path.resolve() for path in args.runtime_path]
    findings.extend(scan_runtime_privacy(runtime_paths, repo_root))
    if args.database_url:
        findings.extend(scan_database(args.database_url, repo_root))
    findings.sort(key=lambda item: (item.audit, item.path, item.line or 0, item.rule))
    report = {
        "schema_version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "git_commit": _git_commit(repo_root),
        "status": "pass" if not findings else "fail",
        "scope": {
            "repository": str(repo_root),
            "runtime_paths": [str(path) for path in runtime_paths],
            "database_scanned": bool(args.database_url),
        },
        "findings": [asdict(finding) for finding in findings],
        "dependencies": dependency_inventory(repo_root),
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "release-audit.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (args.output_dir / "release-audit.md").write_text(_markdown(report), encoding="utf-8")
    print(f"Release audit {report['status']}: {len(findings)} finding(s)")
    return 0 if not findings else 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--runtime-path",
        action="append",
        type=Path,
        default=[],
        help="Log/artifact/volume export to inspect; repeat for multiple paths",
    )
    parser.add_argument(
        "--database-url",
        help=(
            "Optional PostgreSQL URL. Prefer DATABASE_URL expansion in the shell, "
            "not a literal secret."
        ),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/release"))
    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(run(parse_args()))
