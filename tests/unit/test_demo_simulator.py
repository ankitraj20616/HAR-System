from __future__ import annotations

import math

import pytest
from pydantic import ValidationError

from simulator.demo import DemoSettings, generate_chunk


def test_demo_chunks_are_finite_equal_length_and_deterministic() -> None:
    first = generate_chunk(
        sampling_hz=50, chunk_seconds=0.5, elapsed_seconds=15, scenario_seconds=12
    )
    second = generate_chunk(
        sampling_hz=50, chunk_seconds=0.5, elapsed_seconds=15, scenario_seconds=12
    )

    assert first == second
    accel, gyro = first
    assert len(accel) == len(gyro) == 25
    assert all(math.isfinite(axis) for sample in accel + gyro for axis in sample)


@pytest.mark.parametrize(
    "values",
    [
        {"mqtt_port": 0},
        {"simulator_sampling_hz": 0},
        {"simulator_chunk_seconds": 0},
        {"simulator_scenario_seconds": 1},
        {"simulator_device_id": ""},
    ],
)
def test_demo_settings_reject_invalid_startup_configuration(values: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        DemoSettings(**values)
