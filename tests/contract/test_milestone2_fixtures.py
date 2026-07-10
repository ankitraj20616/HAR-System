import json
from pathlib import Path

from shared.schemas import MESSAGE_SCHEMA_VERSION, SensorPrediction, VideoPrediction

FIXTURE = Path(__file__).parents[1] / "fixtures" / "milestone2_predictions.json"


def test_milestone_two_handoff_fixture_is_contract_valid_and_complete() -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))

    assert payload["schema_version"] == MESSAGE_SCHEMA_VERSION
    scenarios = {scenario["name"]: scenario for scenario in payload["scenarios"]}
    assert set(scenarios) == {
        "agreement",
        "disagreement",
        "missing_video_modality",
        "motion_spike",
        "horizontal_transition",
        "ordinary_lying",
    }

    for scenario in scenarios.values():
        SensorPrediction.model_validate(scenario["sensor"])
        if scenario["video"] is not None:
            VideoPrediction.model_validate(scenario["video"])

    assert scenarios["motion_spike"]["sensor"]["motion_intensity"] > 0.9
    assert scenarios["horizontal_transition"]["video"]["orientation"] == "horizontal"
    assert scenarios["ordinary_lying"]["sensor"]["motion_intensity"] < 0.1
