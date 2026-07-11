from __future__ import annotations

import csv
import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.metrics.harness import (
    EvaluationError,
    classification_metrics,
    evaluate_scenario,
    latency_metrics,
    load_scenario,
    match_fall_events,
    render_markdown,
    write_reports,
)

SCENARIO = Path(__file__).parent / "scenarios" / "release_demo_v1.json"


def test_classification_metrics_include_per_class_aggregates_and_matrix() -> None:
    result = classification_metrics(
        ["WALKING", "WALKING", "SITTING"],
        ["WALKING", "SITTING", "SITTING"],
        ["WALKING", "SITTING"],
    )

    assert result["per_class"]["WALKING"] == {
        "precision": 1.0,
        "recall": 0.5,
        "f1": pytest.approx(2 / 3),
        "support": 2,
    }
    assert result["macro_f1"] == pytest.approx((2 / 3 + 2 / 3) / 2)
    assert result["weighted_f1"] == pytest.approx(2 / 3)
    assert result["confusion_matrix"]["rows"] == [[1, 1], [0, 1]]


def test_fall_matching_is_one_to_one_and_counts_duplicate_alerts() -> None:
    ground_truth = [{"id": "fall", "type": "FALL", "ts": "2025-01-01T00:00:10Z"}]
    predictions = [
        {"id": "nearest", "type": "FALL", "ts": "2025-01-01T00:00:10.2Z"},
        {"id": "duplicate", "type": "FALL", "ts": "2025-01-01T00:00:10.4Z"},
        {"id": "false", "type": "FALL", "ts": "2025-01-01T00:00:20Z"},
    ]

    result = match_fall_events(ground_truth, predictions, tolerance_seconds=1.0)

    assert result["true_positives"] == 1
    assert result["false_positives"] == 2
    assert result["duplicate_alerts"] == 1
    assert result["matches"][0]["prediction_id"] == "nearest"
    assert result["precision"] == pytest.approx(1 / 3)
    assert result["recall"] == 1.0


def test_fall_matching_uses_global_nearest_pairs() -> None:
    ground_truth = [
        {"id": "a", "type": "FALL", "ts": "2025-01-01T00:00:10Z"},
        {"id": "b", "type": "FALL", "ts": "2025-01-01T00:00:12Z"},
    ]
    predictions = [
        {"id": "for-b", "type": "FALL", "ts": "2025-01-01T00:00:11.8Z"},
        {"id": "for-a", "type": "FALL", "ts": "2025-01-01T00:00:10.4Z"},
    ]
    result = match_fall_events(ground_truth, predictions, tolerance_seconds=2.0)
    pairs = {(item["ground_truth_id"], item["prediction_id"]) for item in result["matches"]}
    assert pairs == {("a", "for-a"), ("b", "for-b")}


def test_latency_metrics_median_p95_and_max() -> None:
    result = latency_metrics([100, 200, 300, 400])
    assert result["median_ms"] == 250
    assert result["p95_ms"] == pytest.approx(385)
    assert result["max_ms"] == 400
    assert latency_metrics([])["p95_ms"] is None


def test_fixed_scenario_generates_complete_reproducible_report(tmp_path: Path) -> None:
    scenario = load_scenario(SCENARIO)
    report = evaluate_scenario(scenario, started_at=datetime(2025, 6, 1, tzinfo=UTC))

    assert set(report["classification"]) == {"sensor", "video", "raw_fused", "fused"}
    fused_f1 = report["classification"]["fused"]["weighted_f1"]
    assert fused_f1 == 1.0
    assert fused_f1 > report["classification"]["sensor"]["weighted_f1"]
    assert fused_f1 > report["classification"]["video"]["weighted_f1"]
    assert report["fall_events"]["precision"] == 1.0
    assert report["latency"]["fall_event"]["median_ms"] == 1100
    assert len(report["metadata"]["config_hash_sha256"]) == 64
    assert "hardware" in report["metadata"] and "software" in report["metadata"]

    paths = write_reports(report, tmp_path)
    assert set(paths) == {"json", "csv", "markdown"}
    assert (
        json.loads(paths["json"].read_text())["metadata"]["dataset_version"]
        == "release-demo-v1-fixture"
    )
    rows = list(csv.DictReader(paths["csv"].open()))
    assert any(row["metric"] == "duplicate_alerts" for row in rows)
    assert any(row["section"] == "confusion_matrix" for row in rows)
    assert any(row["metric"] == "hardware" for row in rows)
    markdown = paths["markdown"].read_text()
    assert "Confusion matrix" in markdown
    assert "not clinical accuracy claims" in markdown
    assert render_markdown(report) == markdown


def test_non_fall_events_are_not_scored_as_falls_or_required_for_fall_latency() -> None:
    scenario = deepcopy(load_scenario(SCENARIO))
    scenario["ground_truth_events"].append(
        {"id": "inactive-truth", "type": "INACTIVITY", "ts": "2025-06-01T10:01:00Z"}
    )
    scenario["predicted_events"].append(
        {"id": "inactive", "type": "INACTIVITY", "ts": "2025-06-01T10:01:00Z"}
    )

    report = evaluate_scenario(scenario)

    assert report["fall_events"]["true_positives"] == 1
    assert report["fall_events"]["false_positives"] == 0
    assert report["latency"]["fall_event"]["count"] == 1


@pytest.mark.parametrize("event_type", [None, "MEDICAL_EMERGENCY", "fall"])
def test_missing_or_unsupported_event_type_fails_closed(event_type: str | None) -> None:
    scenario = deepcopy(load_scenario(SCENARIO))
    scenario["predicted_events"].append(
        {"id": "invalid-event", "type": event_type, "ts": "2025-06-01T10:01:00Z"}
    )

    with pytest.raises(EvaluationError, match="type must be one of"):
        evaluate_scenario(scenario)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda value: value["metadata"].pop("dataset_version"), "metadata missing"),
        (lambda value: value["samples"][0].update(ground_truth="DANCING"), "unsupported"),
        (
            lambda value: value["samples"][0].update(websocket_ts="2025-06-01T09:59:59Z"),
            "precedes",
        ),
        (lambda value: value["samples"][1].update(id="walk-1"), "duplicate sample id"),
    ],
)
def test_invalid_evidence_fails_closed(mutation, message: str) -> None:
    scenario = deepcopy(load_scenario(SCENARIO))
    mutation(scenario)
    with pytest.raises(EvaluationError, match=message):
        evaluate_scenario(scenario)
