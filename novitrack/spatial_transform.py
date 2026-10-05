"""Reusable calibrated transforms between video pixels and arena coordinates."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _pair(value: Any, name: str) -> np.ndarray:
    pair = np.asarray(value, dtype=float).reshape(-1)
    if pair.size < 2 or not np.all(np.isfinite(pair[:2])):
        raise ValueError(f"{name} must contain two finite values.")
    return pair[:2].copy()


def _points(value: Any) -> np.ndarray:
    points = np.asarray(value, dtype=float)
    if points.ndim == 0 or points.shape[-1] != 2:
        raise ValueError("Coordinates must have a final dimension of length 2.")
    return points


@dataclass(frozen=True, eq=False)
class SpatialTransform:
    """Fixed-arena calibration between source-video pixels and arena metres.

    Pixel and intermediate camera coordinates follow the source image: x grows
    rightward and y downward. Public arena coordinates use a Cartesian frame
    centred on the arena: x grows rightward, y upward, and distances are metres.
    Camera distances and the historical calibration parameters remain in mm.
    """

    image_size_pixels: np.ndarray
    image_offset_pixels: np.ndarray
    distortion_method: str
    distortion: np.ndarray
    arena_center_pixels: np.ndarray
    camera_angle_radians: float = 0.0
    camera_shear: np.ndarray | None = None

    def __post_init__(self) -> None:
        image_size = _pair(self.image_size_pixels, "image_size_pixels")
        if np.any(image_size <= 0):
            raise ValueError("image_size_pixels must be positive.")
        image_offset = _pair(self.image_offset_pixels, "image_offset_pixels")
        arena_center = _pair(self.arena_center_pixels, "arena_center_pixels")
        distortion = np.asarray(self.distortion, dtype=float).reshape(-1).copy()
        method = str(self.distortion_method).strip().casefold()
        if method == "normal":
            if distortion.size < 1 or not np.isfinite(distortion[0]) or distortion[0] == 0:
                raise ValueError("normal distortion requires a finite nonzero scale.")
        elif method == "fisheye_log":
            if distortion.size < 1 or not np.isfinite(distortion[0]) or distortion[0] == 0:
                raise ValueError("fisheye_log distortion requires a finite nonzero factor.")
        elif method in {"fisheye_equidistant", "fisheye_orthographic"}:
            if distortion.size < 2 or not np.all(np.isfinite(distortion[:2])) or np.any(distortion[:2] <= 0):
                raise ValueError(f"{method} distortion requires positive distance and focal length.")
        else:
            raise ValueError(f"Unknown overhead_camera_distortion_method: {method}")
        angle = float(self.camera_angle_radians)
        if not np.isfinite(angle):
            raise ValueError("camera_angle_radians must be finite.")
        shear = np.ones(2) if self.camera_shear is None else _pair(self.camera_shear, "camera_shear")
        if np.any(shear == 0):
            raise ValueError("camera_shear values must be nonzero.")

        for name, value in (
            ("image_size_pixels", image_size),
            ("image_offset_pixels", image_offset),
            ("distortion", distortion),
            ("arena_center_pixels", arena_center),
            ("camera_shear", shear),
        ):
            value.setflags(write=False)
            object.__setattr__(self, name, value)
        object.__setattr__(self, "distortion_method", method)
        object.__setattr__(self, "camera_angle_radians", angle)

    @classmethod
    def from_parameters(cls, params: Any) -> "SpatialTransform":
        """Build a fixed-arena transform from merged NoviTrack parameters."""
        if bool(_get(params, "neurotar", False)):
            raise ValueError(
                "Neurotar pixels-to-arena calibration is time-dependent and cannot use a fixed SpatialTransform."
            )
        return cls(
            image_size_pixels=[
                _get(params, "overhead_camera_width"),
                _get(params, "overhead_camera_height"),
            ],
            image_offset_pixels=_get(params, "overhead_camera_image_offset", [0, 0]),
            distortion_method=_get(params, "overhead_camera_distortion_method", "normal"),
            distortion=_get(params, "overhead_camera_distortion"),
            arena_center_pixels=_get(params, "overhead_arena_center"),
            camera_angle_radians=_get(params, "overhead_camera_angle", 0.0),
            camera_shear=_get(params, "overhead_camera_shear", [1, 1]),
        )

    def overhead_pixels_to_camera_mm(self, points: Any) -> np.ndarray:
        """Undistort source-image points into camera-centred millimetres."""
        shifted = _points(points) - self.image_size_pixels / 2 + self.image_offset_pixels
        x = shifted[..., 0]
        y = shifted[..., 1]
        method = self.distortion_method
        with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
            if method == "normal":
                return shifted / self.distortion[0]
            if method == "fisheye_log":
                sheared = shifted * self.camera_shear
                radius = np.linalg.norm(sheared, axis=-1)
                camera_radius = np.expm1(radius * self.distortion[0]) / self.distortion[0]
                scale = np.divide(camera_radius, radius, out=np.ones_like(radius), where=radius != 0)
                return sheared * scale[..., np.newaxis]

            radius = np.hypot(x, y)
            if method == "fisheye_equidistant":
                camera_radius = self.distortion[0] * np.tan(radius / self.distortion[1])
                valid = np.ones(radius.shape, dtype=bool)
            else:
                valid = radius <= self.distortion[1]
                ratio = np.minimum(radius / self.distortion[1], 1.0)
                camera_radius = self.distortion[0] * np.tan(np.arcsin(ratio))
            scale = np.divide(camera_radius, radius, out=np.ones_like(radius), where=radius != 0)
            camera = shifted * scale[..., np.newaxis]
            return np.where(valid[..., np.newaxis], camera, np.nan)

    def camera_mm_to_overhead_pixels(self, points: Any) -> np.ndarray:
        """Project camera-centred millimetres into source-image pixels."""
        camera = _points(points)
        radius = np.linalg.norm(camera, axis=-1)
        method = self.distortion_method
        with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
            if method == "normal":
                shifted = camera * self.distortion[0]
            else:
                if method == "fisheye_log":
                    overhead_radius = np.log1p(radius * self.distortion[0]) / self.distortion[0]
                elif method == "fisheye_equidistant":
                    overhead_radius = self.distortion[1] * np.arctan(radius / self.distortion[0])
                else:
                    overhead_radius = self.distortion[1] * np.sin(np.arctan(radius / self.distortion[0]))
                scale = np.divide(overhead_radius, radius, out=np.ones_like(radius), where=radius != 0)
                shifted = camera * scale[..., np.newaxis]
                if method == "fisheye_log":
                    shifted = shifted / self.camera_shear
        return shifted + self.image_size_pixels / 2 - self.image_offset_pixels

    def camera_mm_to_arena_m(self, points: Any) -> np.ndarray:
        """Convert camera millimetres to Cartesian arena metres."""
        camera = _points(points)
        center = self.overhead_pixels_to_camera_mm(self.arena_center_pixels)
        relative = camera - center
        alpha = -self.camera_angle_radians
        legacy_x = np.cos(alpha) * relative[..., 0] + np.sin(alpha) * relative[..., 1]
        legacy_y = -np.sin(alpha) * relative[..., 0] + np.cos(alpha) * relative[..., 1]
        return np.stack((legacy_x, -legacy_y), axis=-1) / 1000.0

    def arena_m_to_camera_mm(self, points: Any) -> np.ndarray:
        """Convert Cartesian arena metres to camera-centred millimetres."""
        arena = _points(points)
        legacy_x = arena[..., 0] * 1000.0
        legacy_y = -arena[..., 1] * 1000.0
        alpha = self.camera_angle_radians
        camera_x = np.cos(alpha) * legacy_x + np.sin(alpha) * legacy_y
        camera_y = -np.sin(alpha) * legacy_x + np.cos(alpha) * legacy_y
        center = self.overhead_pixels_to_camera_mm(self.arena_center_pixels)
        return np.stack((camera_x, camera_y), axis=-1) + center

    def overhead_pixels_to_arena_m(self, points: Any) -> np.ndarray:
        """Convert source-image pixels to Cartesian arena metres."""
        return self.camera_mm_to_arena_m(self.overhead_pixels_to_camera_mm(points))

    def arena_m_to_overhead_pixels(self, points: Any) -> np.ndarray:
        """Convert Cartesian arena metres to source-image pixels."""
        return self.camera_mm_to_overhead_pixels(self.arena_m_to_camera_mm(points))

    def metadata(self) -> dict[str, Any]:
        """Return the coordinate contract and calibration values."""
        return {
            "coordinate_system": "arena",
            "units": "m",
            "origin": "arena_center",
            "x_axis": "right",
            "y_axis": "up",
            "camera_intermediate_units": "mm",
            "distortion_method": self.distortion_method,
            "image_size_pixels": tuple(float(value) for value in self.image_size_pixels),
            "image_offset_pixels": tuple(float(value) for value in self.image_offset_pixels),
            "distortion": tuple(float(value) for value in self.distortion),
            "arena_center_pixels": tuple(float(value) for value in self.arena_center_pixels),
            "camera_angle_radians": self.camera_angle_radians,
            "camera_shear": tuple(float(value) for value in self.camera_shear),
        }


__all__ = ["SpatialTransform"]
