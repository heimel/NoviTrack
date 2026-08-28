import numpy as np

from novitrack.load_parameters import load_parameters


def test_load_parameters_applies_explicit_local_config(tmp_path):
    local_config = tmp_path / "processparams_local.py"
    local_config.write_text(
        "\n".join(
            [
                "def processparams_local(params):",
                "    params.networkpathbase = r'C:\\\\local-test-root'",
                "    params.local_config_was_used = True",
                "    return params",
            ]
        ),
        encoding="utf-8",
    )

    params = load_parameters(local_config_file=local_config)

    assert params.networkpathbase == r"C:\\local-test-root"
    assert params.local_config_was_used is True


def test_load_parameters_allows_empty_measures_array():
    record = {
        "setup": "neurotar",
        "date": "2024-01-01",
        "stimulus": "none",
        "measures": np.array([], dtype=object),
    }

    params = load_parameters(record=record)

    assert params is not None


def test_bottom_panel_markers_are_enabled_by_default():
    params = load_parameters(apply_local_overrides=False)

    assert params.nt_show_markers_in_bottom_panels is True
