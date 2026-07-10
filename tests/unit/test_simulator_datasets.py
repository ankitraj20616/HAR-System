from __future__ import annotations

import math
from datetime import UTC
from pathlib import Path

import pytest

from shared.labels import ActivityLabel
from simulator.datasets import DatasetFormatError, SisFallLoader, UciHarLoader, WisdmLoader


def _write_uci_fixture(root: Path) -> None:
    (root / "train" / "Inertial Signals").mkdir(parents=True)
    (root / "activity_labels.txt").write_text(
        "1 WALKING\n2 WALKING_UPSTAIRS\n3 WALKING_DOWNSTAIRS\n4 SITTING\n5 STANDING\n6 LAYING\n",
        encoding="utf-8",
    )
    rows = {
        "total_acc_x": "1 2 3\n4 5 6\n",
        "total_acc_y": "10 20 30\n40 50 60\n",
        "total_acc_z": "100 200 300\n400 500 600\n",
        "body_gyro_x": "0.1 0.2 0.3\n0.4 0.5 0.6\n",
        "body_gyro_y": "1.1 1.2 1.3\n1.4 1.5 1.6\n",
        "body_gyro_z": "2.1 2.2 2.3\n2.4 2.5 2.6\n",
    }
    for signal, content in rows.items():
        (root / "train" / "Inertial Signals" / f"{signal}_train.txt").write_text(
            content, encoding="utf-8"
        )
    (root / "train" / "y_train.txt").write_text("2\n6\n", encoding="utf-8")
    (root / "train" / "subject_train.txt").write_text("1\n2\n", encoding="utf-8")


def test_uci_loader_builds_aligned_windows_and_canonical_labels(tmp_path: Path) -> None:
    root = tmp_path / "UCI HAR Dataset"
    _write_uci_fixture(root)

    windows = list(UciHarLoader(tmp_path, splits=("train",), window_stride=2))

    assert len(windows) == 2
    assert windows[0].accel[1] == (2.0, 20.0, 200.0)
    assert windows[0].gyro[2] == (0.3, 1.3, 2.3)
    assert windows[0].canonical_label is ActivityLabel.WALKING
    assert windows[1].canonical_label is ActivityLabel.LYING
    assert windows[0].timestamp.tzinfo is UTC
    assert (windows[1].timestamp - windows[0].timestamp).total_seconds() == pytest.approx(0.04)
    assert windows[1].scenario_id == "uci-train-subject-02-window-000002"


def test_uci_loader_rejects_misaligned_source_files(tmp_path: Path) -> None:
    _write_uci_fixture(tmp_path)
    path = tmp_path / "train" / "Inertial Signals" / "body_gyro_z_train.txt"
    path.write_text("2.1 2.2 2.3\n", encoding="utf-8")

    with pytest.raises(DatasetFormatError, match="different row counts"):
        list(UciHarLoader(tmp_path, splits=("train",), window_stride=2))


def test_wisdm_loader_windows_segments_and_supplies_zero_gyro(tmp_path: Path) -> None:
    path = tmp_path / "wisdm.txt"
    path.write_text(
        "1,Walking,100,1,2,3;\n"
        "1,Walking,101,4,5,6;\n"
        "1,Walking,102,7,8,9;\n"
        "1,Walking,103,10,11,12;\n"
        "1,Sitting,104,13,14,15;\n"
        "1,Sitting,105,16,17,18;\n",
        encoding="utf-8",
    )

    windows = list(WisdmLoader(path, window_size=3, window_stride=2))

    assert len(windows) == 1
    assert windows[0].canonical_label is ActivityLabel.WALKING
    assert windows[0].accel[-1] == pytest.approx((7 / 9.80665, 8 / 9.80665, 9 / 9.80665))
    assert windows[0].gyro == ((0.0, 0.0, 0.0),) * 3
    assert windows[0].scenario_id == "wisdm-user-1-segment-0001"


def test_wisdm_strict_and_tolerant_malformed_row_modes(tmp_path: Path) -> None:
    path = tmp_path / "wisdm.txt"
    path.write_text("bad row\n1,Standing,1,1,2,3;\n", encoding="utf-8")

    with pytest.raises(DatasetFormatError, match="expected user,label,timestamp,x,y,z"):
        list(WisdmLoader(path, window_size=1, window_stride=1))
    tolerant = list(WisdmLoader(path, window_size=1, window_stride=1, strict=False))
    assert len(tolerant) == 1
    assert tolerant[0].canonical_label is ActivityLabel.STANDING


def test_sisfall_loader_preserves_fall_ground_truth_and_maps_adl(tmp_path: Path) -> None:
    (tmp_path / "F01_SA01_R01.txt").write_text("1,2,3,4,5,6;\n7,8,9,10,11,12;\n", encoding="utf-8")
    (tmp_path / "D14_SA01_R01.txt").write_text(
        "13,14,15,16,17,18;\n19,20,21,22,23,24;\n", encoding="utf-8"
    )

    windows = list(SisFallLoader(tmp_path, window_size=2, window_stride=1))
    by_scenario = {window.scenario_id: window for window in windows}

    assert by_scenario["F01_SA01_R01"].source_label == "FALL"
    assert by_scenario["F01_SA01_R01"].canonical_label is ActivityLabel.UNKNOWN
    assert by_scenario["D14_SA01_R01"].canonical_label is ActivityLabel.LYING
    assert by_scenario["D14_SA01_R01"].accel[0] == pytest.approx((13 / 256, 14 / 256, 15 / 256))
    assert by_scenario["D14_SA01_R01"].gyro[0] == pytest.approx(
        tuple(math.radians(value / 14.375) for value in (16, 17, 18))
    )
