from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from novitrack.change_times import (
    change_neurotar_to_video_times,
    change_times,
    change_video_to_neurotar_times,
)


class TestNtChangeTimes(unittest.TestCase):
    def test_preserves_shape_and_flattens_triggers(self) -> None:
        from_times = np.array([[0.0, 1.0, 2.0], [3.0, 4.0, 5.0]])
        triggers_from = np.array([[0.0, 10.0, 20.0]])
        triggers_to = np.array([[5.0], [17.0], [29.0]])

        changed, offset, multiplier = change_times(from_times, triggers_from, triggers_to)

        self.assertEqual(changed.shape, from_times.shape)
        np.testing.assert_allclose(changed, from_times * 1.2 + 5.0)
        self.assertTrue(np.isclose(offset, 5.0))
        self.assertTrue(np.isclose(multiplier, 1.2))

    def test_aligns_missing_first_from_trigger(self) -> None:
        from_times = np.array([20.0, 31.0])
        triggers_from = np.array([0.0, 8.0, 20.0, 31.0])
        triggers_to = np.array([102.0, 222.0, 332.0])

        changed, offset, multiplier = change_times(from_times, triggers_from, triggers_to)

        np.testing.assert_allclose(changed, [222.0, 332.0])
        self.assertTrue(np.isclose(offset, 22.0))
        self.assertTrue(np.isclose(multiplier, 10.0))

    def test_aligns_missing_last_to_trigger(self) -> None:
        from_times = np.array([0.0, 10.0])
        triggers_from = np.array([0.0, 10.0, 20.0])
        triggers_to = np.array([1.0, 21.0, 41.0, 501.0])

        changed, offset, multiplier = change_times(from_times, triggers_from, triggers_to)

        np.testing.assert_allclose(changed, [1.0, 21.0])
        self.assertTrue(np.isclose(offset, 1.0))
        self.assertTrue(np.isclose(multiplier, 2.0))

    def test_single_trigger_uses_supplied_multipliers(self) -> None:
        changed, offset, multiplier = change_times(
            np.array([1.0, 2.0]),
            np.array([10.0]),
            np.array([20.0]),
            multiplier_from=2.0,
            multiplier_to=4.0,
        )

        np.testing.assert_allclose(changed, [2.0, 4.0])
        self.assertTrue(np.isclose(offset, 0.0))
        self.assertTrue(np.isclose(multiplier, 2.0))

    def test_can_log_sync_pair_fit_diagnostics(self) -> None:
        messages = []
        with patch("novitrack.change_times.logmsg", side_effect=messages.append):
            change_times(
                [15.0],
                [10.0, 20.0, 30.0],
                [100.0, 120.0, 140.0],
                diagnostic_label="RWD marker alignment",
            )

        output = "\n".join(messages)
        self.assertIn("10 -> 100, 20 -> 120, 30 -> 140", output)
        self.assertIn("master_time = 2 * source_time + 80 s", output)
        self.assertIn("clock multiplier 2", output)
        self.assertIn("sync fit correlation 1", output)
        self.assertIn("residual RMS", output)

    def test_warns_when_maximum_sync_residual_exceeds_20_ms(self) -> None:
        messages = []
        with patch("novitrack.change_times.logmsg", side_effect=messages.append):
            change_times(
                [0.0],
                [0.0, 1.0, 2.0],
                [0.0, 1.0, 2.1],
                diagnostic_label="RWD marker alignment",
            )

        output = "\n".join(messages)
        self.assertIn("WARNING: RWD marker alignment maximum sync residual", output)
        self.assertIn("exceeds 20 ms", output)

    def test_deprecated_video_neurotar_wrappers(self) -> None:
        params = SimpleNamespace(picamera_time_multiplier=2.0)

        np.testing.assert_allclose(
            change_video_to_neurotar_times(np.array([12.0, 14.0]), np.array([10.0]), params),
            [1.0, 2.0],
        )
        np.testing.assert_allclose(
            change_neurotar_to_video_times(np.array([1.0, 2.0]), np.array([10.0]), params),
            [12.0, 14.0],
        )


if __name__ == "__main__":
    unittest.main()
