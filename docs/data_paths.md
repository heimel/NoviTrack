# Data paths and local configuration

Both the Python and MATLAB implementations expect session data to be organized
below a local or network data root. Configure this root locally:

- Python: use `processparams_local.py` on your Python path, or pass an override
  YAML file to `load_parameters`.
- MATLAB: use `processparams_local.m`, created by `load_invivotools`.

The important parameter is:

```text
networkpathbase = YOUR_DATA_FOLDER
```

Session paths are then built from database fields such as `project`, `dataset`,
`subject`, and `sessionid`.

Return to the [manual index](README.md).
