"""Concrete local-only TFLite execution for the pinned HAR adapter.

Nothing in this module downloads artifacts. ``SENSOR_MODEL_PATH`` must point to
an already-provisioned ``.tflite`` file and ``SENSOR_MODEL_LABELS`` must declare
its output class order. The interpreter dependency is imported lazily.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from threading import Lock
from typing import Any


class LocalModelError(RuntimeError):
    pass


class TFLiteModelRunner:
    """Validate and execute one local FLOAT32 ``[1, time, 3, 1]`` model."""

    def __init__(
        self,
        model_path: Path,
        labels: Sequence[str],
        interpreter_factory: Callable[..., Any] | None = None,
    ) -> None:
        if model_path.suffix.lower() != ".tflite":
            raise LocalModelError("SENSOR_MODEL_PATH must be a .tflite file")
        if not model_path.is_file():
            raise LocalModelError("configured local model file does not exist")
        if not labels:
            raise LocalModelError("configured local model class order is empty")
        factory = interpreter_factory or _interpreter_factory()
        try:
            self._interpreter = factory(model_path=str(model_path))
            self._interpreter.allocate_tensors()
            inputs = self._interpreter.get_input_details()
            outputs = self._interpreter.get_output_details()
        except Exception as exc:
            raise LocalModelError(f"TFLite initialization failed ({type(exc).__name__})") from exc
        if len(inputs) != 1 or len(outputs) != 1:
            raise LocalModelError("TFLite model must expose exactly one input and one output")
        shape = tuple(int(value) for value in inputs[0]["shape"])
        if len(shape) != 4 or shape[0] not in {1, -1} or shape[2:] != (3, 1):
            raise LocalModelError("TFLite input must have shape [1, time, 3, 1]")
        try:
            import numpy as np

            if np.dtype(inputs[0].get("dtype")) != np.dtype("float32"):
                raise LocalModelError("TFLite input must use FLOAT32 values")
        except TypeError as exc:
            raise LocalModelError("TFLite input dtype is invalid") from exc
        if shape[1] < 20:
            raise LocalModelError("TFLite input window must contain at least 20 samples")
        output_shape = tuple(int(value) for value in outputs[0]["shape"])
        if not output_shape or output_shape[-1] != len(labels):
            raise LocalModelError("SENSOR_MODEL_LABELS count does not match model output")
        self._input = inputs[0]
        self._output = outputs[0]
        self._window_size = shape[1]
        self._labels = tuple(labels)
        self._lock = Lock()

    def __call__(
        self,
        accel_window: Sequence[tuple[float, float, float]],
        _features: Mapping[str, float],
    ) -> Mapping[str, float]:
        if not accel_window:
            raise LocalModelError("cannot infer an empty accelerometer window")
        values = _resample(accel_window, self._window_size)
        if not all(math.isfinite(axis) for sample in values for axis in sample):
            raise LocalModelError("model input contains a non-finite value")
        try:
            import numpy as np

            tensor = np.asarray(values, dtype=self._input["dtype"]).reshape(
                (1, self._window_size, 3, 1)
            )
            with self._lock:
                self._interpreter.set_tensor(self._input["index"], tensor)
                self._interpreter.invoke()
                scores = np.asarray(
                    self._interpreter.get_tensor(self._output["index"]), dtype=float
                ).reshape(-1)
        except Exception as exc:
            raise LocalModelError(f"TFLite inference failed ({type(exc).__name__})") from exc
        probabilities = _as_probabilities([float(score) for score in scores])
        return dict(zip(self._labels, probabilities, strict=True))


def _resample(
    values: Sequence[tuple[float, float, float]], target_size: int
) -> list[tuple[float, float, float]]:
    """Linearly resample configurable service windows to the artifact input length."""

    if len(values) == target_size:
        return list(values)
    if len(values) == 1:
        return [values[0]] * target_size
    scale = (len(values) - 1) / (target_size - 1)
    result: list[tuple[float, float, float]] = []
    for target_index in range(target_size):
        position = target_index * scale
        left = int(position)
        right = min(left + 1, len(values) - 1)
        weight = position - left
        result.append(
            tuple(
                values[left][axis] * (1.0 - weight) + values[right][axis] * weight
                for axis in range(3)
            )
        )
    return result


def _as_probabilities(scores: Sequence[float]) -> list[float]:
    if not scores or not all(math.isfinite(score) for score in scores):
        raise LocalModelError("model output must contain finite class scores")
    total = math.fsum(scores)
    if all(0.0 <= score <= 1.0 for score in scores) and math.isclose(
        total, 1.0, rel_tol=1e-4, abs_tol=1e-4
    ):
        return list(scores)
    maximum = max(scores)
    exponentials = [math.exp(score - maximum) for score in scores]
    denominator = math.fsum(exponentials)
    return [value / denominator for value in exponentials]


def _interpreter_factory() -> Callable[..., Any]:
    try:
        from ai_edge_litert.interpreter import Interpreter

        return Interpreter
    except ImportError:
        try:
            from tflite_runtime.interpreter import Interpreter

            return Interpreter
        except ImportError:
            try:
                from tensorflow.lite import Interpreter

                return Interpreter
            except ImportError as exc:
                raise LocalModelError(
                    "local LiteRT runtime is not installed; install ai-edge-litert"
                ) from exc


def load_local_tflite(path: Path, labels: Sequence[str]) -> TFLiteModelRunner:
    """Build a local runner without resolving a URL or Hub repository."""

    return TFLiteModelRunner(path, labels)
