"""Dependency-free metrics and report generation for fixed HAR scenarios.

The input contract deliberately keeps ground truth in separate fields from every
prediction.  This module only evaluates captured results; it never invokes an
inference service, which prevents labels leaking into model inputs.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import subprocess
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from statistics import median
from typing import Any

from shared.labels import CANONICAL_ACTIVITIES, CANONICAL_EVENTS, map_activity_label

PREDICTION_FIELDS = (
    "sensor_prediction",
    "video_prediction",
    "raw_fused_prediction",
    "smoothed_fused_prediction",
)
DISPLAY_NAMES = {
    "sensor_prediction": "sensor",
    "video_prediction": "video",
    "raw_fused_prediction": "raw_fused",
    "smoothed_fused_prediction": "fused",
}


class EvaluationError(ValueError):
    """Raised when scenario evidence is incomplete or internally inconsistent."""


def _utc(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise EvaluationError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise EvaluationError(f"{field} must include a timezone")
    return parsed.astimezone(UTC)


def _label(value: object, field: str) -> str:
    label = map_activity_label(value).value
    if label == "UNKNOWN" and str(value).strip().upper() != "UNKNOWN":
        raise EvaluationError(f"{field} contains unsupported activity label {value!r}")
    return label


def load_scenario(path: str | Path) -> dict[str, Any]:
    """Load and minimally validate a fixed scenario capture."""

    source = Path(path)
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvaluationError(f"cannot read scenario {source}: {exc}") from exc
    if not isinstance(data, dict):
        raise EvaluationError("scenario root must be a JSON object")
    samples = data.get("samples")
    if not isinstance(samples, list) or not samples:
        raise EvaluationError("scenario samples must be a non-empty list")
    if not isinstance(data.get("ground_truth_events", []), list):
        raise EvaluationError("ground_truth_events must be a list")
    if not isinstance(data.get("predicted_events", []), list):
        raise EvaluationError("predicted_events must be a list")
    return data


def _safe_ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def classification_metrics(
    truth: Sequence[str], predictions: Sequence[str], labels: Sequence[str]
) -> dict[str, Any]:
    """Compute per-class and macro/weighted metrics with zero-division = 0."""

    if len(truth) != len(predictions) or not truth:
        raise EvaluationError("classification inputs must have equal, non-zero length")
    matrix = [[0 for _ in labels] for _ in labels]
    indexes = {label: index for index, label in enumerate(labels)}
    for expected, predicted in zip(truth, predictions, strict=True):
        matrix[indexes[expected]][indexes[predicted]] += 1

    per_class: dict[str, dict[str, float | int]] = {}
    for index, label in enumerate(labels):
        tp = matrix[index][index]
        support = sum(matrix[index])
        predicted_count = sum(row[index] for row in matrix)
        precision = _safe_ratio(tp, predicted_count)
        recall = _safe_ratio(tp, support)
        f1 = _safe_ratio(2 * precision * recall, precision + recall)
        per_class[label] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": support,
        }

    macro = sum(float(item["f1"]) for item in per_class.values()) / len(labels)
    total = len(truth)
    weighted = sum(float(item["f1"]) * int(item["support"]) for item in per_class.values()) / total
    accuracy = sum(matrix[i][i] for i in range(len(labels))) / total
    return {
        "per_class": per_class,
        "macro_f1": macro,
        "weighted_f1": weighted,
        "accuracy": accuracy,
        "confusion_matrix": {"labels": list(labels), "rows": matrix},
        "sample_count": total,
        "averaging_policy": "macro includes all canonical classes; weighted uses truth support",
    }


def match_fall_events(
    ground_truth: Sequence[Mapping[str, Any]],
    predicted: Sequence[Mapping[str, Any]],
    tolerance_seconds: float,
) -> dict[str, Any]:
    """Match each predicted fall to at most one truth event, nearest pair first."""

    if not math.isfinite(tolerance_seconds) or tolerance_seconds < 0:
        raise EvaluationError("fall_match_tolerance_seconds must be finite and non-negative")
    validated_truth = _validated_events(list(ground_truth), "ground_truth_events")
    validated_predictions = _validated_events(list(predicted), "predicted_events")
    ground_truth = [item for item in validated_truth if item["type"] == "FALL"]
    predicted = [item for item in validated_predictions if item["type"] == "FALL"]
    gt_times = [
        _utc(str(item.get("ts", "")), f"ground_truth_events[{i}].ts")
        for i, item in enumerate(ground_truth)
    ]
    prediction_times = [
        _utc(str(item.get("ts", "")), f"predicted_events[{i}].ts")
        for i, item in enumerate(predicted)
    ]
    candidates = sorted(
        (
            (abs((prediction_ts - truth_ts).total_seconds()), truth_i, prediction_i)
            for truth_i, truth_ts in enumerate(gt_times)
            for prediction_i, prediction_ts in enumerate(prediction_times)
            if abs((prediction_ts - truth_ts).total_seconds()) <= tolerance_seconds
        ),
        key=lambda item: (item[0], item[1], item[2]),
    )
    used_truth: set[int] = set()
    used_predictions: set[int] = set()
    matches: list[dict[str, Any]] = []
    for distance, truth_i, prediction_i in candidates:
        if truth_i in used_truth or prediction_i in used_predictions:
            continue
        used_truth.add(truth_i)
        used_predictions.add(prediction_i)
        matches.append(
            {
                "ground_truth_id": ground_truth[truth_i].get("id", truth_i),
                "prediction_id": predicted[prediction_i].get("id", prediction_i),
                "absolute_delta_seconds": distance,
            }
        )

    unmatched_predictions = set(range(len(predicted))) - used_predictions
    duplicate_indexes = {
        prediction_i
        for prediction_i in unmatched_predictions
        if any(
            abs((prediction_times[prediction_i] - truth_ts).total_seconds()) <= tolerance_seconds
            for truth_ts in gt_times
        )
    }
    tp = len(matches)
    precision = _safe_ratio(tp, len(predicted))
    recall = _safe_ratio(tp, len(ground_truth))
    return {
        "precision": precision,
        "recall": recall,
        "f1": _safe_ratio(2 * precision * recall, precision + recall),
        "true_positives": tp,
        "false_positives": len(predicted) - tp,
        "false_negatives": len(ground_truth) - tp,
        "duplicate_alerts": len(duplicate_indexes),
        "tolerance_seconds": tolerance_seconds,
        "matches": matches,
    }


def _percentile(values: Sequence[float], percentile: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def latency_metrics(latencies_ms: Sequence[float]) -> dict[str, float | int | str | None]:
    """Summarize latency using linear-interpolated p95."""

    if not latencies_ms:
        return {"count": 0, "median_ms": None, "p95_ms": None, "max_ms": None}
    if any(not math.isfinite(value) or value < 0 for value in latencies_ms):
        raise EvaluationError("latencies must be finite and non-negative")
    return {
        "count": len(latencies_ms),
        "median_ms": median(latencies_ms),
        "p95_ms": _percentile(latencies_ms, 0.95),
        "max_ms": max(latencies_ms),
        "percentile_policy": "linear interpolation at rank (n-1)*p",
    }


def _latency_from_records(records: Iterable[Mapping[str, Any]], prefix: str) -> list[float]:
    values: list[float] = []
    for index, item in enumerate(records):
        source = _utc(str(item.get("source_ts", "")), f"{prefix}[{index}].source_ts")
        received = _utc(str(item.get("websocket_ts", "")), f"{prefix}[{index}].websocket_ts")
        milliseconds = (received - source).total_seconds() * 1000
        if milliseconds < 0:
            raise EvaluationError(f"{prefix}[{index}] websocket_ts precedes source_ts")
        values.append(milliseconds)
    return values


def _validated_events(value: Sequence[object], field: str) -> list[Mapping[str, Any]]:
    events: list[Mapping[str, Any]] = []
    ids: set[object] = set()
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise EvaluationError(f"{field}[{index}] must be an object")
        event_type = item.get("type")
        if event_type not in CANONICAL_EVENTS:
            raise EvaluationError(
                f"{field}[{index}].type must be one of {', '.join(CANONICAL_EVENTS)}"
            )
        event_id = item.get("id", index)
        if event_id in ids:
            raise EvaluationError(f"duplicate {field} id {event_id!r}")
        ids.add(event_id)
        events.append(item)
    return events


def _git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def _config_hash(config: object) -> str:
    canonical = json.dumps(config, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


def evaluate_scenario(
    scenario: Mapping[str, Any], *, started_at: datetime | None = None
) -> dict[str, Any]:
    """Evaluate a captured scenario and attach reproducibility metadata."""

    started = (started_at or datetime.now(UTC)).astimezone(UTC)
    samples = scenario.get("samples")
    if not isinstance(samples, list) or not samples:
        raise EvaluationError("scenario samples must be a non-empty list")
    labels = list(CANONICAL_ACTIVITIES)
    truth: list[str] = []
    predictions: dict[str, list[str]] = {field: [] for field in PREDICTION_FIELDS}
    ids: set[object] = set()
    for index, sample in enumerate(samples):
        if not isinstance(sample, dict):
            raise EvaluationError(f"samples[{index}] must be an object")
        sample_id = sample.get("id", index)
        if sample_id in ids:
            raise EvaluationError(f"duplicate sample id {sample_id!r}")
        ids.add(sample_id)
        truth.append(_label(sample.get("ground_truth"), f"samples[{index}].ground_truth"))
        for field in PREDICTION_FIELDS:
            predictions[field].append(_label(sample.get(field), f"samples[{index}].{field}"))

    classification = {
        DISPLAY_NAMES[field]: classification_metrics(truth, values, labels)
        for field, values in predictions.items()
    }
    config = scenario.get("config", {})
    if not isinstance(config, dict):
        raise EvaluationError("config must be an object")
    tolerance = float(config.get("fall_match_tolerance_seconds", 2.0))
    ground_truth_events = scenario.get("ground_truth_events", [])
    predicted_events = scenario.get("predicted_events", [])
    if not isinstance(ground_truth_events, list) or not isinstance(predicted_events, list):
        raise EvaluationError("event collections must be lists")
    validated_truth = _validated_events(ground_truth_events, "ground_truth_events")
    validated_predictions = _validated_events(predicted_events, "predicted_events")
    fall_predictions = [item for item in validated_predictions if item["type"] == "FALL"]

    activity_latency = _latency_from_records(samples, "samples")
    event_latency = _latency_from_records(fall_predictions, "predicted_fall_events")
    supplied = scenario.get("metadata", {})
    if not isinstance(supplied, dict):
        raise EvaluationError("metadata must be an object")
    required = ("dataset", "dataset_version", "model_id", "model_revision", "seed")
    missing = [key for key in required if key not in supplied]
    if missing:
        raise EvaluationError(f"metadata missing required fields: {', '.join(missing)}")
    finished = datetime.now(UTC)
    metadata = {
        **supplied,
        "git_commit": _git_commit(),
        "config_hash_sha256": _config_hash(config),
        "sample_count": len(samples),
        "hardware": supplied.get(
            "hardware",
            {"machine": platform.machine(), "processor": platform.processor() or "unknown"},
        ),
        "software": supplied.get(
            "software",
            {"python": platform.python_version(), "platform": platform.platform()},
        ),
        "started_at": started.isoformat().replace("+00:00", "Z"),
        "finished_at": finished.isoformat().replace("+00:00", "Z"),
    }
    return {
        "schema_version": "1.0",
        "metadata": metadata,
        "scenario_selection": scenario.get("scenario_selection", []),
        "label_mapping": scenario.get("label_mapping", {}),
        "config": config,
        "classification": classification,
        "fall_events": match_fall_events(validated_truth, validated_predictions, tolerance),
        "latency": {
            "activity": latency_metrics(activity_latency),
            "fall_event": latency_metrics(event_latency),
            "overall": latency_metrics([*activity_latency, *event_latency]),
            "definition": "source/event timestamp to dashboard-receivable WebSocket timestamp",
        },
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    """Render a compact, human-readable release evidence summary."""

    metadata = report["metadata"]
    lines = [
        "# HAR Metrics Summary",
        "",
        "> Academic demo evaluation; these results are not clinical accuracy claims.",
        "",
        "## Run metadata",
        "",
        f"- Dataset: {metadata['dataset']} ({metadata['dataset_version']})",
        f"- Model: {metadata['model_id']} ({metadata['model_revision']})",
        f"- Samples: {metadata['sample_count']}",
        f"- Seed: {metadata['seed']}",
        f"- Git commit: `{metadata['git_commit']}`",
        f"- Config SHA-256: `{metadata['config_hash_sha256']}`",
        f"- Hardware: `{json.dumps(metadata['hardware'], sort_keys=True)}`",
        f"- Software: `{json.dumps(metadata['software'], sort_keys=True)}`",
        f"- Started: {metadata['started_at']}",
        f"- Finished: {metadata['finished_at']}",
        f"- Scenarios: {', '.join(report['scenario_selection'])}",
        f"- Label mapping: `{json.dumps(report['label_mapping'], sort_keys=True)}`",
        f"- Frozen config: `{json.dumps(report['config'], sort_keys=True)}`",
        "",
        "## Classification",
        "",
        "| Modality | Macro F1 | Weighted F1 | Accuracy |",
        "|---|---:|---:|---:|",
    ]
    for name, result in report["classification"].items():
        lines.append(
            f"| {name} | {result['macro_f1']:.4f} | "
            f"{result['weighted_f1']:.4f} | {result['accuracy']:.4f} |"
        )
    for name, result in report["classification"].items():
        lines.extend(
            [
                "",
                f"### {name}",
                "",
                "| Class | Precision | Recall | F1 | Support |",
                "|---|---:|---:|---:|---:|",
            ]
        )
        for label, item in result["per_class"].items():
            lines.append(
                f"| {label} | {item['precision']:.4f} | {item['recall']:.4f} | "
                f"{item['f1']:.4f} | {item['support']} |"
            )
        matrix = result["confusion_matrix"]
        labels = matrix["labels"]
        lines.extend(["", "Confusion matrix (truth rows, prediction columns):", ""])
        lines.append("| Truth \\ Pred | " + " | ".join(labels) + " |")
        lines.append("|---|" + "---:|" * len(labels))
        for label, row in zip(labels, matrix["rows"], strict=True):
            lines.append(f"| {label} | " + " | ".join(map(str, row)) + " |")

    fall = report["fall_events"]
    lines.extend(
        [
            "",
            "## Fall events",
            "",
            f"One-to-one nearest matching within {fall['tolerance_seconds']:.3f} seconds.",
            "",
            "| Precision | Recall | F1 | TP | FP | FN | Duplicate alerts |",
            "|---:|---:|---:|---:|---:|---:|---:|",
            f"| {fall['precision']:.4f} | {fall['recall']:.4f} | {fall['f1']:.4f} | "
            f"{fall['true_positives']} | {fall['false_positives']} | "
            f"{fall['false_negatives']} | {fall['duplicate_alerts']} |",
            "",
            "## Latency",
            "",
            "| Signal | Count | Median ms | P95 ms | Max ms |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for name in ("activity", "fall_event", "overall"):
        item = report["latency"][name]
        format_value = lambda value: "n/a" if value is None else f"{value:.2f}"  # noqa: E731
        lines.append(
            f"| {name} | {item['count']} | {format_value(item['median_ms'])} | "
            f"{format_value(item['p95_ms'])} | {format_value(item['max_ms'])} |"
        )
    return "\n".join(lines) + "\n"


def write_reports(report: Mapping[str, Any], output_dir: str | Path) -> dict[str, Path]:
    """Atomically-ish write JSON, long-form CSV, and Markdown reports."""

    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    json_path = destination / "metrics.json"
    csv_path = destination / "metrics.csv"
    markdown_path = destination / "summary.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=("section", "modality", "class", "metric", "value", "support"),
        )
        writer.writeheader()
        for metric in (
            "dataset",
            "dataset_version",
            "model_id",
            "model_revision",
            "seed",
            "git_commit",
            "config_hash_sha256",
            "sample_count",
            "hardware",
            "software",
            "started_at",
            "finished_at",
        ):
            value = report["metadata"][metric]
            if isinstance(value, dict):
                value = json.dumps(value, sort_keys=True)
            writer.writerow(
                {
                    "section": "metadata",
                    "modality": "",
                    "class": "",
                    "metric": metric,
                    "value": value,
                    "support": "",
                }
            )
        for modality, result in report["classification"].items():
            for label, item in result["per_class"].items():
                for metric in ("precision", "recall", "f1"):
                    writer.writerow(
                        {
                            "section": "classification",
                            "modality": modality,
                            "class": label,
                            "metric": metric,
                            "value": item[metric],
                            "support": item["support"],
                        }
                    )
            for metric in ("macro_f1", "weighted_f1", "accuracy"):
                writer.writerow(
                    {
                        "section": "classification",
                        "modality": modality,
                        "class": "ALL",
                        "metric": metric,
                        "value": result[metric],
                        "support": result["sample_count"],
                    }
                )
            matrix = result["confusion_matrix"]
            for truth_label, row in zip(matrix["labels"], matrix["rows"], strict=True):
                for prediction_label, count in zip(matrix["labels"], row, strict=True):
                    writer.writerow(
                        {
                            "section": "confusion_matrix",
                            "modality": modality,
                            "class": truth_label,
                            "metric": f"predicted_{prediction_label}",
                            "value": count,
                            "support": sum(row),
                        }
                    )
        for metric in (
            "precision",
            "recall",
            "f1",
            "true_positives",
            "false_positives",
            "false_negatives",
            "duplicate_alerts",
        ):
            writer.writerow(
                {
                    "section": "fall_events",
                    "modality": "fused",
                    "class": "FALL",
                    "metric": metric,
                    "value": report["fall_events"][metric],
                    "support": "",
                }
            )
        for signal in ("activity", "fall_event", "overall"):
            for metric in ("median_ms", "p95_ms", "max_ms"):
                writer.writerow(
                    {
                        "section": "latency",
                        "modality": signal,
                        "class": "ALL",
                        "metric": metric,
                        "value": report["latency"][signal][metric],
                        "support": report["latency"][signal]["count"],
                    }
                )
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    return {"json": json_path, "csv": csv_path, "markdown": markdown_path}
