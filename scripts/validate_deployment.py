#!/usr/bin/env python3
"""Fail fast when release dependencies or container references are not pinned."""

from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
EXACT_REQUIREMENT = re.compile(r"^[A-Za-z0-9_.-]+(?:\[[A-Za-z0-9_,.-]+\])?==[^\s]+$")


def _requirements(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def validate_python_dependencies(errors: list[str]) -> None:
    runtime = _requirements(ROOT / "requirements.txt")
    development = _requirements(ROOT / "requirements-dev.txt")
    for path, lines in (("requirements.txt", runtime), ("requirements-dev.txt", development)):
        for line in lines:
            if line.startswith("-r "):
                continue
            if not EXACT_REQUIREMENT.fullmatch(line):
                errors.append(f"{path}: dependency is not exactly pinned: {line}")

    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    if project["project"]["dependencies"] != runtime:
        errors.append("pyproject.toml runtime dependencies differ from requirements.txt")
    pyproject_dev = project["dependency-groups"]["dev"]
    requirements_dev = [line for line in development if not line.startswith("-r ")]
    if pyproject_dev != requirements_dev:
        errors.append("pyproject.toml dev dependencies differ from requirements-dev.txt")


def validate_dashboard_dependencies(errors: list[str]) -> None:
    package = json.loads((ROOT / "dashboard/package.json").read_text(encoding="utf-8"))
    lock = json.loads((ROOT / "dashboard/package-lock.json").read_text(encoding="utf-8"))
    locked_root = lock["packages"][""]
    for group in ("dependencies", "devDependencies"):
        declared = package.get(group, {})
        if declared != locked_root.get(group, {}):
            errors.append(f"dashboard/package-lock.json root {group} is out of sync")
        for name, version in declared.items():
            if version == "latest" or version.startswith(("^", "~", ">", "<", "*")):
                errors.append(f"dashboard/package.json: {name} is not exactly pinned")


def validate_container_references(errors: list[str]) -> None:
    paths = (ROOT / "Dockerfile", ROOT / "dashboard/Dockerfile", ROOT / "docker-compose.yml")
    for path in paths:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip()
            reference = None
            if stripped.startswith("FROM "):
                reference = stripped.split()[1]
            elif stripped.startswith("image:") and "${" not in stripped:
                reference = stripped.removeprefix("image:").strip()
            if reference is not None and (":" not in reference or reference.endswith(":latest")):
                errors.append(f"{path.relative_to(ROOT)}:{number}: unpinned image {reference}")
            if reference is not None and ":" in reference:
                tag = reference.rsplit(":", maxsplit=1)[1]
                numeric_release = tag.split("-", maxsplit=1)[0]
                if numeric_release.isdigit():
                    errors.append(
                        f"{path.relative_to(ROOT)}:{number}: broad major-only image {reference}"
                    )


def validate_settings(errors: list[str]) -> None:
    from services.feedback_service.config import FeedbackSettings
    from services.fusion_service.config import FusionSettings
    from services.sensor_service.config import SensorSettings
    from services.video_service.config import VideoSettings
    from simulator.demo import DemoSettings

    for settings_type in (
        SensorSettings,
        VideoSettings,
        FusionSettings,
        FeedbackSettings,
        DemoSettings,
    ):
        try:
            settings_type()
        except Exception as exc:  # pragma: no cover - command-line failure reporting
            errors.append(f"{settings_type.__name__} defaults are invalid: {type(exc).__name__}")


def main() -> int:
    errors: list[str] = []
    validate_python_dependencies(errors)
    validate_dashboard_dependencies(errors)
    validate_container_references(errors)
    validate_settings(errors)
    if errors:
        print("Deployment validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Deployment configuration and dependency pins are valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
