"""Canonical search-box geometry shared by preview, validation, and engines."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace
from math import isfinite
from typing import Literal

Coordinate = tuple[float, float, float]
SearchBoxSource = Literal["user", "reference_ligand", "binding_site", "imported"]


@dataclass(frozen=True, slots=True)
class CoordinateViolation:
    atom_label: str
    axis: Literal["x", "y", "z"]
    value: float
    minimum: float
    maximum: float


@dataclass(frozen=True, slots=True)
class CoordinateValidation:
    violations: tuple[CoordinateViolation, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.violations


@dataclass(frozen=True, slots=True)
class SearchBox:
    """An immutable axis-aligned docking box in the prepared receptor frame."""

    center: Coordinate
    size: Coordinate
    coordinate_frame: str
    margin: float
    source: SearchBoxSource

    def __post_init__(self) -> None:
        if len(self.center) != 3 or len(self.size) != 3:
            raise ValueError("center and size must contain exactly three values")
        if not all(isfinite(value) for value in (*self.center, *self.size, self.margin)):
            raise ValueError("search box values must be finite")
        if any(value <= 0 for value in self.size):
            raise ValueError("size values must be positive")
        if not self.coordinate_frame:
            raise ValueError("coordinate_frame is required")
        if self.margin < 0:
            raise ValueError("margin must not be negative")

    @property
    def minimum(self) -> Coordinate:
        return tuple(center - size / 2 for center, size in zip(self.center, self.size, strict=True))  # type: ignore[return-value]

    @property
    def maximum(self) -> Coordinate:
        return tuple(center + size / 2 for center, size in zip(self.center, self.size, strict=True))  # type: ignore[return-value]

    @classmethod
    def fit_to_coordinates(
        cls,
        coordinates: Iterable[Coordinate],
        coordinate_frame: str,
        margin: float,
        source: SearchBoxSource = "reference_ligand",
    ) -> SearchBox:
        values = tuple(coordinates)
        if not values:
            raise ValueError("at least one coordinate is required")
        if any(len(point) != 3 or not all(isfinite(v) for v in point) for point in values):
            raise ValueError("coordinates must contain three finite values")
        minima = tuple(min(point[index] for point in values) for index in range(3))
        maxima = tuple(max(point[index] for point in values) for index in range(3))
        center = tuple(
            (minimum + maximum) / 2 for minimum, maximum in zip(minima, maxima, strict=True)
        )
        size = tuple(
            maximum - minimum + 2 * margin for minimum, maximum in zip(minima, maxima, strict=True)
        )
        return cls(
            center=center,
            size=size,
            coordinate_frame=coordinate_frame,
            margin=margin,
            source=source,
        )

    def validate_coordinates(
        self, coordinates: Iterable[tuple[str, Coordinate]], tolerance: float = 0.0
    ) -> CoordinateValidation:
        if not isfinite(tolerance) or tolerance < 0:
            raise ValueError("tolerance must not be negative")
        minimum = self.minimum
        maximum = self.maximum
        violations: list[CoordinateViolation] = []
        for atom_label, point in coordinates:
            if len(point) != 3:
                raise ValueError("coordinates must contain three values")
            for index, axis in enumerate(("x", "y", "z")):
                if (
                    not isfinite(point[index])
                    or point[index] < minimum[index] - tolerance
                    or point[index] > maximum[index] + tolerance
                ):
                    violations.append(
                        CoordinateViolation(
                            atom_label=atom_label,
                            axis=axis,
                            value=point[index],
                            minimum=minimum[index],
                            maximum=maximum[index],
                        )
                    )
        return CoordinateValidation(tuple(violations))

    def with_center(self, center: Coordinate, source: SearchBoxSource = "user") -> SearchBox:
        return replace(self, center=center, source=source)
