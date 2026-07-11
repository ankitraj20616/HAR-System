"""CLI entry point: python -m tests.metrics."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .harness import (
    EvaluationError,
    evaluate_scenario,
    load_scenario,
    render_markdown,
    write_reports,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate a fixed labeled HAR scenario capture")
    parser.add_argument("scenario", type=Path, help="scenario JSON input")
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/metrics"))
    args = parser.parse_args(argv)
    try:
        report = evaluate_scenario(load_scenario(args.scenario))
        paths = write_reports(report, args.output_dir)
    except EvaluationError as exc:
        parser.exit(2, f"metrics error: {exc}\n")
    sys.stdout.write(render_markdown(report))
    sys.stdout.write("\nArtifacts:\n")
    for kind, path in paths.items():
        sys.stdout.write(f"- {kind}: {path}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
