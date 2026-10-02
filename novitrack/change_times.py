"""Convert timestamps between NoviTrack time reference frames."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np

from inpythotools.logmsg import logmsg


def _readonly_vector(value: Any) -> np.ndarray:
    vector = np.asarray(value, dtype=float).reshape(-1).copy()
    vector.setflags(write=False)
    return vector


@dataclass(frozen=True)
class ClockTransform:
    """Fitted affine mapping between two named clock coordinate systems."""

    source_clock: str
    target_clock: str
    offset: float
    multiplier: float
    source_triggers: np.ndarray
    target_triggers: np.ndarray
    residuals: np.ndarray

    def __post_init__(self) -> None:
        if not np.isfinite(self.offset):
            raise ValueError("ClockTransform offset must be finite.")
        if not np.isfinite(self.multiplier) or self.multiplier == 0:
            raise ValueError("ClockTransform multiplier must be finite and nonzero.")
        object.__setattr__(self, "source_triggers", _readonly_vector(self.source_triggers))
        object.__setattr__(self, "target_triggers", _readonly_vector(self.target_triggers))
        object.__setattr__(self, "residuals", _readonly_vector(self.residuals))
        if self.source_triggers.size != self.target_triggers.size:
            raise ValueError("ClockTransform trigger arrays must have equal lengths.")
        if self.residuals.size != self.source_triggers.size:
            raise ValueError("ClockTransform residuals must align with its triggers.")

    def apply(self, times: Any) -> np.ndarray:
        """Convert ``times`` from the source clock to the target clock."""
        return np.asarray(times, dtype=float) * self.multiplier + self.offset

    def inverse(self) -> "ClockTransform":
        """Return the exact analytical inverse without fitting the triggers again."""
        inverse_multiplier = 1.0 / self.multiplier
        inverse_offset = -self.offset * inverse_multiplier
        inverse_residuals = self.source_triggers - (
            self.target_triggers * inverse_multiplier + inverse_offset
        )
        return ClockTransform(
            source_clock=self.target_clock,
            target_clock=self.source_clock,
            offset=inverse_offset,
            multiplier=inverse_multiplier,
            source_triggers=self.target_triggers,
            target_triggers=self.source_triggers,
            residuals=inverse_residuals,
        )

    @property
    def residual_rms(self) -> float:
        if self.residuals.size == 0:
            return np.nan
        return float(np.sqrt(np.mean(np.square(self.residuals))))

    @property
    def maximum_absolute_residual(self) -> float:
        if self.residuals.size == 0:
            return np.nan
        return float(np.max(np.abs(self.residuals)))


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _as_vector(value: Any) -> np.ndarray:
    return np.asarray(value, dtype=float).reshape(-1)


def _correlation(x: np.ndarray, y: np.ndarray) -> float:
    """Return MATLAB-like corrcoef(x, y)[0, 1], tolerating short vectors."""
    if x.size < 2 or y.size < 2:
        return np.nan
    if np.nanstd(x) == 0 or np.nanstd(y) == 0:
        return np.nan
    return float(np.corrcoef(x, y)[0, 1])


def _prefer_tail_alignment(longer: np.ndarray, shorter: np.ndarray) -> bool:
    """Choose whether a longer trigger vector should be tail-aligned."""
    n_long = longer.size
    n_short = shorter.size
    cc_missing_first = _correlation(longer[n_long - n_short :], shorter)
    cc_missing_last = _correlation(longer[:n_short], shorter)

    if np.isnan(cc_missing_first) and np.isnan(cc_missing_last):
        return False
    if np.isnan(cc_missing_last):
        return True
    if np.isnan(cc_missing_first):
        return False
    return cc_missing_first > cc_missing_last


def _log_alignment_diagnostics(
    label: str,
    triggers_from: np.ndarray,
    triggers_to: np.ndarray,
    original_from_count: int,
    original_to_count: int,
    offset: float,
    multiplier: float,
    *,
    multiplier_was_supplied: bool,
) -> None:
    pairs = ", ".join(
        f"{source:.6g} -> {target:.6g}"
        for source, target in zip(triggers_from, triggers_to)
    )
    matched_count = triggers_from.size
    logmsg(
        f"{label}: matched {matched_count}/{original_from_count} source sync pulse(s) "
        f"to {matched_count}/{original_to_count} reference sync pulse(s) "
        f"(source -> reference, s): {pairs}."
    )
    clock_difference = 100.0 * (multiplier - 1.0)
    logmsg(
        f"{label}: reference_time = {multiplier:.12g} * source_time + "
        f"{offset:.9g} s; clock multiplier {multiplier:.12g}, "
        f"difference from 1 is {clock_difference:+.6g}%."
    )
    if matched_count < 2:
        origin = (
            "supplied clock multipliers"
            if multiplier_was_supplied
            else "an assumed multiplier of 1"
        )
        logmsg(
            f"{label}: only one sync-pulse pair is available; clock drift cannot "
            f"be measured and the fit uses {origin}."
        )
        return

    residuals = triggers_to - (multiplier * triggers_from + offset)
    rms_ms = 1000.0 * float(np.sqrt(np.mean(np.square(residuals))))
    max_ms = 1000.0 * float(np.max(np.abs(residuals)))
    correlation = _correlation(triggers_from, triggers_to)
    logmsg(
        f"{label}: sync fit correlation {correlation:.9g}, residual RMS "
        f"{rms_ms:.6g} ms, maximum absolute residual {max_ms:.6g} ms."
    )
    if max_ms > 20.0:
        logmsg(
            f"WARNING: {label} maximum sync residual is {max_ms:.6g} ms, "
            "which exceeds 20 ms. The time alignment may be inaccurate."
        )


def fit_clock_transform(
    triggers_from: Any,
    triggers_to: Any,
    multiplier_from: float | None = None,
    multiplier_to: float | None = None,
    *,
    source_clock: str = "source",
    target_clock: str = "reference",
    diagnostic_label: str | None = None,
) -> ClockTransform:
    """Fit an affine transform between two clocks from synchronization pulses."""
    triggers_from_vec = _as_vector(triggers_from)
    triggers_to_vec = _as_vector(triggers_to)

    n_triggers_from = triggers_from_vec.size
    n_triggers_to = triggers_to_vec.size
    original_from_count = n_triggers_from
    original_to_count = n_triggers_to
    multiplier_was_supplied = multiplier_from is not None and multiplier_to is not None

    if n_triggers_from == 0 or n_triggers_to == 0:
        raise ValueError("fit_clock_transform requires at least one trigger in both clocks.")

    if n_triggers_from == 1 and n_triggers_to > 1:
        logmsg("Detected too many triggers TO. Using only the first! May be wrong trigger. If so edit trigger log.")
        triggers_to_vec = triggers_to_vec[:1]
        n_triggers_to = 1
    if n_triggers_to == 1 and n_triggers_from > 1:
        logmsg("Detected too many triggers FROM. Using only the first! May be wrong trigger. If so edit trigger log.")
        triggers_from_vec = triggers_from_vec[:1]
        n_triggers_from = 1

    if n_triggers_from > n_triggers_to:
        if _prefer_tail_alignment(triggers_from_vec, triggers_to_vec):
            triggers_from_vec = triggers_from_vec[n_triggers_from - n_triggers_to :]
            logmsg("Missed first FROM triggers in TO reference")
        else:
            triggers_from_vec = triggers_from_vec[:n_triggers_to]
            logmsg("Missed last FROM triggers in TO reference")
        n_triggers_from = triggers_from_vec.size

    if n_triggers_from < n_triggers_to:
        if _prefer_tail_alignment(triggers_to_vec, triggers_from_vec):
            triggers_to_vec = triggers_to_vec[n_triggers_to - n_triggers_from :]
            logmsg("Missed first TO triggers in FROM reference")
        else:
            triggers_to_vec = triggers_to_vec[:n_triggers_from]
            logmsg("Missed last TO triggers in FROM reference")
        n_triggers_to = triggers_to_vec.size

    matched_triggers_from = triggers_from_vec.copy()
    matched_triggers_to = triggers_to_vec.copy()

    fit_triggers_from = triggers_from_vec
    fit_triggers_to = triggers_to_vec
    if n_triggers_from == 1:
        if multiplier_from is None or multiplier_to is None:
            logmsg(
                "Only single matching trigger and no multipliers given. "
                "Assuming them to be 1. This is inaccurate for large times."
            )
            multiplier_from = 1.0
            multiplier_to = 1.0
        fit_triggers_from = np.array(
            [triggers_from_vec[0], triggers_from_vec[0] + 1000 * float(multiplier_from)],
            dtype=float,
        )
        fit_triggers_to = np.array(
            [triggers_to_vec[0], triggers_to_vec[0] + 1000 * float(multiplier_to)],
            dtype=float,
        )

    cc = _correlation(fit_triggers_from, fit_triggers_to)
    if not np.isnan(cc) and cc < 0.999:
        logmsg(
            f"Only correlation of {cc:.3g} between TO and FROM triggers. "
            "This suggest missing triggers and inaccurate time change."
        )

    x = np.column_stack((np.ones(fit_triggers_from.size), fit_triggers_from))
    offset, multiplier = np.linalg.lstsq(x, fit_triggers_to, rcond=None)[0]
    offset = float(offset)
    multiplier = float(multiplier)

    if abs(multiplier - 1) > 0.01:
        logmsg("Clocks are more than 1% different. There is a likely mismatch of triggers.")

    if diagnostic_label is not None:
        _log_alignment_diagnostics(
            diagnostic_label,
            matched_triggers_from,
            matched_triggers_to,
            original_from_count,
            original_to_count,
            offset,
            multiplier,
            multiplier_was_supplied=multiplier_was_supplied,
        )

    residuals = matched_triggers_to - (
        matched_triggers_from * multiplier + offset
    )
    return ClockTransform(
        source_clock=source_clock,
        target_clock=target_clock,
        offset=offset,
        multiplier=multiplier,
        source_triggers=matched_triggers_from,
        target_triggers=matched_triggers_to,
        residuals=residuals,
    )


def change_times(
    from_times: Any,
    triggers_from: Any,
    triggers_to: Any,
    multiplier_from: float | None = None,
    multiplier_to: float | None = None,
    *,
    diagnostic_label: str | None = None,
) -> tuple[np.ndarray, float, float]:
    """Change timestamps from one reference frame to another.

    This mirrors MATLAB ``change_times.m``:

    ``to = multiplier * from_times + offset``

    Trigger arrays are internally flattened so row/column orientation does not
    affect the alignment, matching the recent MATLAB-side normalization.
    """
    transform = fit_clock_transform(
        triggers_from,
        triggers_to,
        multiplier_from,
        multiplier_to,
        diagnostic_label=diagnostic_label,
    )
    changed = transform.apply(from_times)
    return changed, transform.offset, transform.multiplier


def change_video_to_neurotar_times(video_t: Any, trigger_times: Any, params: Any) -> np.ndarray:
    """Deprecated MATLAB-compatible wrapper for video-to-neurotar time conversion."""
    logmsg("DEPRECATED: CHANGE CODE TO USE change_times")
    trigger_times_vec = _as_vector(trigger_times)
    if trigger_times_vec.size == 0:
        raise ValueError("trigger_times must contain at least one value.")
    return (np.asarray(video_t, dtype=float) - trigger_times_vec[0]) / float(_get(params, "picamera_time_multiplier"))


def change_neurotar_to_video_times(neurotar_t: Any, trigger_times: Any, params: Any) -> np.ndarray:
    """Deprecated MATLAB-compatible wrapper for neurotar-to-video time conversion."""
    trigger_times_vec = _as_vector(trigger_times)
    if trigger_times_vec.size == 0:
        raise ValueError("trigger_times must contain at least one value.")
    return float(_get(params, "picamera_time_multiplier")) * np.asarray(neurotar_t, dtype=float) + trigger_times_vec[0]


__all__ = [
    "ClockTransform",
    "change_times",
    "change_video_to_neurotar_times",
    "change_neurotar_to_video_times",
    "fit_clock_transform",
]
