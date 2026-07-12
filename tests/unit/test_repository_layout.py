from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_milestone_one_repository_boundaries_exist() -> None:
    required_directories = (
        "services/sensor_service",
        "services/video_service",
        "services/fusion_service",
        "services/feedback_service",
        "services/auth_service",
        "shared",
        "simulator",
        "dashboard",
        "tests/unit",
        "tests/contract",
        "tests/integration",
        "data",
    )

    missing = [path for path in required_directories if not (PROJECT_ROOT / path).is_dir()]
    assert not missing, f"Missing Milestone 1 repository directories: {missing}"
