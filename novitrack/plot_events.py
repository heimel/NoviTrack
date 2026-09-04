"""Plot NoviTrack per-event analysis results."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import numpy as np
import pandas as pd

from .get_events import get_events
from .plot_photometry import channel_metadata_lines


_EVENT_METADATA_KEYS = {"parameters", "duration"}

_PARAMETER_UNITS = {
    "frequency": "Hz",
    "pulse_width": "s",
    "power": "W",
}


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _as_array(value: Any) -> np.ndarray:
    return np.asarray(value, dtype=float).reshape(-1)


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, np.ndarray):
        return value.size == 0
    try:
        return len(value) == 0
    except TypeError:
        return False


def _marker_table(params: Any) -> pd.DataFrame:
    markers = _get(params, "markers", pd.DataFrame())
    if isinstance(markers, pd.DataFrame):
        return markers
    return pd.DataFrame(markers)


def _event_description(params: Any, event_type: str) -> str:
    markers = _marker_table(params)
    if markers.empty or "marker_id" not in markers:
        return event_type
    match = markers[markers["marker_id"].astype(str) == event_type]
    if match.empty:
        return event_type
    return str(match.iloc[0].get("description", event_type))


def _display_name(name: str) -> str:
    """Turn a stored snake-case field name into a concise plot label."""
    words = str(name).split("_")
    return " ".join("ID" if word.lower() == "id" else word.capitalize() for word in words)


def _parameter_label(name: str) -> str:
    unit = _PARAMETER_UNITS.get(name)
    label_name = name
    if unit is None and "_" in name:
        candidate_name, candidate_unit = name.rsplit("_", 1)
        if candidate_unit.lower() in {"nm", "um", "mm", "cm", "m", "ms", "s", "hz", "w"}:
            label_name = candidate_name
            unit = candidate_unit
    label = _display_name(label_name)
    return f"{label} ({unit})" if unit else label


def _plot_parameter_values(ax: plt.Axes, values: np.ndarray, responses: np.ndarray) -> None:
    """Scatter aligned responses against numeric or categorical parameter values."""
    valid_response = np.isfinite(responses)
    try:
        numeric_values = np.asarray(values, dtype=float)
    except (TypeError, ValueError):
        categories = np.asarray([str(value) for value in values], dtype=object)
        missing = pd.isna(values)
        valid = valid_response & ~np.asarray(missing, dtype=bool)
        labels = list(dict.fromkeys(categories[valid]))
        positions = {label: index for index, label in enumerate(labels)}
        x = np.asarray([positions.get(label, np.nan) for label in categories], dtype=float)
        ax.scatter(x[valid], responses[valid], color="black", alpha=0.75)
        ax.set_xticks(range(len(labels)), labels)
        return

    valid = valid_response & np.isfinite(numeric_values)
    ax.scatter(numeric_values[valid], responses[valid], color="black", alpha=0.75)


def _plot_parameter_figures(
    event_type: str,
    event: Mapping[str, Any],
    observables: list[str],
    params: Any,
    snippet_units: Mapping[str, Any],
) -> list[plt.Figure]:
    """Plot trial responses for each parameter stored as a varying array."""
    parameters = _get(event, "parameters", {})
    if not isinstance(parameters, Mapping):
        return []

    figures: list[plt.Figure] = []
    for parameter_name, raw_values in parameters.items():
        values = np.asarray(raw_values).reshape(-1)
        if values.size <= 1:
            continue

        aligned_observables = [
            observable
            for observable in observables
            if _as_array(event[observable].get("event_mean", [])).size == values.size
        ]
        if not aligned_observables:
            continue

        n_cols = min(3, len(aligned_observables))
        n_rows = int(np.ceil(len(aligned_observables) / n_cols))
        fig, axes = plt.subplots(
            n_rows,
            n_cols,
            figsize=(4.5 * n_cols, 3.8 * n_rows),
            num=f"{event_type}: {parameter_name}",
            constrained_layout=True,
            squeeze=False,
        )
        fig.set_label(f"event_{event_type}_by_{parameter_name}")
        fig.suptitle(f"{_event_description(params, event_type)} by {_display_name(str(parameter_name))}")

        for ax, observable in zip(axes.flat, aligned_observables):
            result = event[observable]
            responses = _as_array(result["event_mean"])
            _plot_parameter_values(ax, values, responses)
            unit = snippet_units.get(observable, result.get("unit", "")) or ""
            response_label = f"{_display_name(observable)} event mean"
            ax.set_title(_display_name(observable))
            ax.set_xlabel(_parameter_label(str(parameter_name)))
            ax.set_ylabel(f"{response_label} ({unit})" if unit else response_label)
            ax.grid(axis="both", color="0.9", linewidth=0.8)
            ax.spines[["top", "right"]].set_visible(False)

        for ax in axes.flat[len(aligned_observables) :]:
            ax.axis("off")
        figures.append(fig)
    return figures


def plot_events(
    record: Mapping[str, Any],
    params: Any,
    snippets: Mapping[str, Any] | None = None,
) -> list[plt.Figure]:
    """Plot per-event heatmaps and mean traces for all event observables."""
    measures = _get(record, "measures", {})
    event_measures = _get(measures, "event", {})
    if _is_empty(event_measures):
        return []

    events = get_events(measures, params)
    t = _as_array(_get(measures, "snippets_tbins"))
    figures: list[plt.Figure] = []
    snippets_data = _get(snippets, "data", {}) if snippets else {}
    snippet_units = _get(snippets, "unit", {}) if snippets else {}

    for event_type, event in event_measures.items():
        observables = [name for name in event if name not in _EVENT_METADATA_KEYS]
        if not observables:
            continue
        n_cols = min(3, len(observables))
        n_rows = int(np.ceil(len(observables) / n_cols))
        channels = list(_get(measures, "channels", []))
        info_height = 0.25 + 0.14 * sum(len(channel_metadata_lines(channel)) for channel in channels)
        fig = plt.figure(
            figsize=(4.5 * n_cols, 4.2 * n_rows + info_height),
            num=str(event_type),
            constrained_layout=True,
        )
        fig.set_label(f"event_{event_type}")
        fig.suptitle(_event_description(params, str(event_type)))
        event_indices = events.index[events["event"] == str(event_type)].to_numpy()
        if channels:
            grid = GridSpec(
                n_rows + 1,
                n_cols,
                figure=fig,
                height_ratios=[max(info_height, 0.6)] + [4.2] * n_rows,
            )
            info_ax = fig.add_subplot(grid[0, :])
            channel_blocks = ["\n".join(channel_metadata_lines(channel)) for channel in channels]
            info_ax.text(
                0.0,
                1.0,
                f"{_get(record, 'sessionid', '')}\n\n" + "\n\n".join(channel_blocks),
                ha="left",
                va="top",
                transform=info_ax.transAxes,
            )
            info_ax.axis("off")
            plot_row_offset = 1
        else:
            grid = GridSpec(n_rows, n_cols, figure=fig)
            plot_row_offset = 0

        for index, observable in enumerate(observables):
            row = index // n_cols
            col = index % n_cols
            subgrid = grid[row + plot_row_offset, col].subgridspec(2, 1, height_ratios=[2.0, 1.0], hspace=0.05)
            heat_ax = fig.add_subplot(subgrid[0])
            trace_ax = fig.add_subplot(subgrid[1], sharex=heat_ax)
            result = event[observable]
            if observable in snippets_data and event_indices.size:
                heat_ax.imshow(
                    np.asarray(snippets_data[observable])[event_indices, :],
                    aspect="auto",
                    interpolation="nearest",
                    extent=[t[0], t[-1], event_indices.size + 0.5, 0.5],
                )
                heat_ax.set_ylim(event_indices.size + 0.5, 0.5)
                heat_ax.set_yticks(np.unique([1, event_indices.size]))
            else:
                heat_ax.text(0.5, 0.5, "No snippets", ha="center", va="center", transform=heat_ax.transAxes)
                heat_ax.set_yticks([])
            heat_ax.set_title(f"{observable}, n = {result.get('n', '')}")
            heat_ax.set_ylabel("Trial")
            heat_ax.tick_params(axis="x", labelbottom=False)
            heat_ax.spines[["top", "right"]].set_visible(False)

            y = _as_array(result["snippet_mean"])
            sem = _as_array(result.get("snippet_sem", np.zeros_like(y)))
            trace_ax.plot(t, y, color="black", linewidth=1.5)
            trace_ax.fill_between(t, y - 1.97 * sem, y + 1.97 * sem, color="black", alpha=0.18, linewidth=0)
            trace_ax.axhline(0, color="0.4", linewidth=0.8)
            trace_ax.axvline(0, color="0.4", linewidth=0.8)
            trace_ax.set_xlabel("Time (s)")
            trace_ax.set_ylabel(snippet_units.get(observable, result.get("unit", "")))
            trace_ax.spines[["top", "right"]].set_visible(False)

        for index in range(len(observables), n_rows * n_cols):
            blank_ax = fig.add_subplot(grid[index // n_cols + plot_row_offset, index % n_cols])
            blank_ax.axis("off")
        figures.append(fig)
        figures.extend(
            _plot_parameter_figures(
                str(event_type),
                event,
                observables,
                params,
                snippet_units,
            )
        )
    return figures


__all__ = ["plot_events"]
