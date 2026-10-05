from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from novitrack.compute_locations import change_overhead_to_arena_coordinates
from novitrack.spatial_transform import SpatialTransform


def _params(**overrides):
    values = {
        "neurotar": False,
        "overhead_camera_width": 100,
        "overhead_camera_height": 80,
        "overhead_camera_image_offset": [0, 0],
        "overhead_camera_distortion_method": "normal",
        "overhead_camera_distortion": [2.0, np.nan],
        "overhead_camera_shear": [1.0, 1.0],
        "overhead_camera_angle": 0.0,
        "overhead_arena_center": [50, 40],
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_fixed_arena_transform_uses_metres_and_cartesian_y_axis() -> None:
    transform = SpatialTransform.from_parameters(_params())

    arena = transform.overhead_pixels_to_arena_m([[70, 20], [30, 60]])

    np.testing.assert_allclose(arena, [[0.01, 0.01], [-0.01, -0.01]])
    np.testing.assert_allclose(transform.arena_m_to_overhead_pixels(arena), [[70, 20], [30, 60]])
    assert transform.metadata()["units"] == "m"
    assert transform.metadata()["y_axis"] == "up"


def test_canonical_arena_matches_legacy_geometry_with_explicit_unit_and_y_conversion() -> None:
    params = _params(overhead_camera_angle=-0.2, overhead_arena_center=[47, 42])
    pixels = np.array([[10.0, 20.0], [50.0, 40.0], [80.0, 65.0]])
    legacy_x, legacy_y = change_overhead_to_arena_coordinates(
        pixels[:, 0], pixels[:, 1], params
    )

    arena = SpatialTransform.from_parameters(params).overhead_pixels_to_arena_m(pixels)

    np.testing.assert_allclose(arena[:, 0], legacy_x / 1000.0)
    np.testing.assert_allclose(arena[:, 1], -legacy_y / 1000.0)


@pytest.mark.parametrize(
    ("method", "distortion", "shear"),
    [
        ("normal", [1.4, np.nan], [1.0, 1.0]),
        ("fisheye_log", [0.002], [1.1, 0.9]),
        ("fisheye_equidistant", [300.0, 250.0], [1.0, 1.0]),
        ("fisheye_orthographic", [300.0, 250.0], [1.0, 1.0]),
    ],
)
def test_camera_projection_round_trip(method, distortion, shear) -> None:
    transform = SpatialTransform.from_parameters(
        _params(
            overhead_camera_distortion_method=method,
            overhead_camera_distortion=distortion,
            overhead_camera_shear=shear,
        )
    )
    pixels = np.array([[50.0, 40.0], [55.0, 35.0], [65.0, 52.0]])

    camera = transform.overhead_pixels_to_camera_mm(pixels)

    np.testing.assert_allclose(
        transform.camera_mm_to_overhead_pixels(camera), pixels, atol=1e-10
    )


def test_orthographic_points_outside_calibrated_view_are_nan() -> None:
    transform = SpatialTransform.from_parameters(
        _params(
            overhead_camera_distortion_method="fisheye_orthographic",
            overhead_camera_distortion=[300.0, 20.0],
        )
    )

    result = transform.overhead_pixels_to_arena_m([[100.0, 80.0]])

    assert np.isnan(result).all()


def test_neurotar_requires_a_time_dependent_transform() -> None:
    with pytest.raises(ValueError, match="time-dependent"):
        SpatialTransform.from_parameters(_params(neurotar=True))
