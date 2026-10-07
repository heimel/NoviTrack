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

## DeepLabCut GPU worker

The behavioral-tracking client writes one JSON job per video below
`nt_deeplabcut_queue_folder/pending`. On the Windows GPU VM, activate the
DeepLabCut 3.0.1 environment and run from the NoviTrack repository:

```powershell
conda activate deeplabcut
python novitrack/deeplabcut_worker.py --until-empty
```

The worker claims jobs atomically and moves their manifests through `running`,
`completed`, or `failed`. It processes one video at a time, writes HDF5 and DLC
metadata beside the source video, copies the selected configuration to
`DLC/<camera>/config.yaml` in the session, and stores one log per job below the
queue's `logs` directory. It does not create CSV or labeled-video output.

The queue path can be overridden on the VM in `processparams_local.py`:

```python
def processparams_local(params):
    params.nt_deeplabcut_queue_folder = r"\\server\share\Communication\DeepLabCut"
    return params
```

No path mapping is needed while the VM uses the same Windows UNC paths as the
client. If a future Linux VM mounts the share under another path, configure
one or more longest-prefix mappings locally:

```python
def processparams_local(params):
    params.nt_deeplabcut_path_mappings = [
        [r"\\vs03.herseninstituut.knaw.nl\VS03-CSF-1", "/mnt/vs03"],
    ]
    return params
```

The worker also supports `--once`, `--job JOB_ID`, `--queue-folder`,
`--parameters`, and `--local-config`. A failed job remains in `failed` with its
exception and traceback; it can be queued again by the client.

Return to the [manual index](README.md).
