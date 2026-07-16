"""Numeric pose landmark types and reusable geometry helpers."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Landmark:
    """One normalized pose point; it deliberately cannot contain image data."""

    x: float
    y: float
    z: float = 0.0
    visibility: float = 1.0

    def __post_init__(self) -> None:
        if not all(math.isfinite(value) for value in (self.x, self.y, self.z, self.visibility)):
            raise ValueError("landmark values must be finite")
        if not 0.0 <= self.visibility <= 1.0:
            raise ValueError("landmark visibility must be between 0 and 1")

    @property
    def in_frame(self) -> bool:
        """Whether this point actually lies inside the captured image.

        Pose estimators extrapolate joints they cannot see rather than omitting
        them, placing them outside the normalized 0-1 image box while still
        reporting near-perfect visibility. Such a point is a guess, not an
        observation, so geometry derived from it is meaningless.
        """

        return 0.0 <= self.x <= 1.0 and 0.0 <= self.y <= 1.0


class PoseLandmarks:
    """Immutable, name-addressable numeric output from a pose estimator."""

    def __init__(self, points: Mapping[str, Landmark]) -> None:
        self._points = dict(points)

    def get(self, name: str, min_visibility: float = 0.0) -> Landmark | None:
        point = self._points.get(name)
        if point is None or not point.in_frame:
            return None
        return point if point.visibility >= min_visibility else None

    def require(
        self, names: Iterable[str], min_visibility: float = 0.0
    ) -> tuple[Landmark, ...] | None:
        points = tuple(self.get(name, min_visibility) for name in names)
        if any(point is None for point in points):
            return None
        return tuple(point for point in points if point is not None)

    def visible(self, min_visibility: float = 0.0) -> dict[str, Landmark]:
        return {
            name: point
            for name, point in self._points.items()
            if point.in_frame and point.visibility >= min_visibility
        }

    def __len__(self) -> int:
        return len(self._points)


def midpoint(first: Landmark, second: Landmark) -> Landmark:
    """Return a visibility-conservative midpoint."""

    return Landmark(
        x=(first.x + second.x) / 2.0,
        y=(first.y + second.y) / 2.0,
        z=(first.z + second.z) / 2.0,
        visibility=min(first.visibility, second.visibility),
    )


def three_point_angle(first: Landmark, vertex: Landmark, third: Landmark) -> float:
    """Return the smaller 0-180 degree angle ``first-vertex-third``.

    Degenerate segments have no meaningful angle and therefore raise a clear
    error rather than introducing NaNs into downstream confidence calculations.
    """

    first_vector = (first.x - vertex.x, first.y - vertex.y)
    third_vector = (third.x - vertex.x, third.y - vertex.y)
    first_length = math.hypot(*first_vector)
    third_length = math.hypot(*third_vector)
    if first_length <= 1e-12 or third_length <= 1e-12:
        raise ValueError("cannot calculate an angle from coincident landmarks")
    cosine = sum(a * b for a, b in zip(first_vector, third_vector, strict=True)) / (
        first_length * third_length
    )
    return math.degrees(math.acos(max(-1.0, min(1.0, cosine))))


def point_distance(first: Landmark, second: Landmark) -> float:
    return math.hypot(first.x - second.x, first.y - second.y)
