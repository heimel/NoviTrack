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
