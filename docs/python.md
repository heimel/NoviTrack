# Python installation and usage

The Python implementation in `novitrack` is the primary NoviTrack development
path.

## Installation

Create a conda environment with Python 3.11 and PyQt6:

```bash
conda create -n pyqt6_env python=3.11 pyqt6 -y -c conda-forge
conda activate pyqt6_env
```

Install the remaining dependencies:

```bash
conda install -y -c conda-forge pandas scipy matplotlib statsmodels pytest openpyxl nptdms pyqtgraph opencv spyder-kernels jupyter ipykernel pyyaml
```

Download the following repositories:

- [heimel/InPythoTools](https://github.com/heimel/InPythoTools)
- [heimel/NoviTrack](https://github.com/heimel/NoviTrack)

NoviTrack depends on the reusable Python tools in the separate `InPythoTools`
repository. Make sure that repository is importable, for example by adding its
folder to `PYTHONPATH` or by opening Python from a workspace where both
repositories are on the Python path.

For one Python session, replace `...` with the actual path:

```python
import sys
sys.path.append(r"C:\Users\...\InPythoTools;C:\Users\...\NoviTrack")

import novitrack as nt
```

For persistent use in the conda environment, replace `...` with the actual path:

```powershell
conda activate pyqt6_env
conda env config vars set PYTHONPATH="C:\Users\...\InPythoTools;C:\Users\...\NoviTrack"
conda deactivate
conda activate pyqt6_env
```

Test the path from the NoviTrack repository root:

```powershell
python -c "import novitrack as nt; from inpythotools import browse_database; print(nt.experiment_db, browse_database)"
```

See [Data paths and local configuration](data_paths.md) to configure the data
root.

## Usage

From the NoviTrack repository root:

```python
import novitrack as nt

browser = nt.experiment_db()
```

This opens the database browser using `test_data/nttestdb_examples.mat` when no
filename is supplied.

The current record can be accessed with:

```python
record = browser.current_record()
```

### VS Code interactive workflow

To use a MATLAB-like interactive workflow in VS Code, install the Python and
Jupyter extensions. First select the conda environment with Ctrl-Shift-P,
`Python: Select Interpreter`, and choose `pyqt6_env`. Then create a Jupyter
terminal with `Jupyter: Create Interactive Window`.

In a fresh Interactive Window or notebook kernel, enable Qt windows before
importing `novitrack`, then start the database browser with `experiment_db`:

```python
%matplotlib qt
%gui qt

import novitrack as nt

browser = nt.experiment_db(block=False)
```

This returns to the prompt while keeping the database browser responsive. The
`%matplotlib qt` line makes result figures open as separate Qt windows when
clicking buttons such as `Results`.

To make this automatic for new VS Code Jupyter kernels, add the startup
commands to VS Code User Settings, not workspace settings. The setting has
application scope, so open `Preferences: Open User Settings (JSON)` and add:

```json
"jupyter.runStartupCommands": [
  "%gui qt",
  "%matplotlib qt"
]
```

Restart the Jupyter kernel after changing this setting.

### Basic analysis

```python
import novitrack as nt

db = nt.load_mat_database("test_data/nttestdb_examples.mat")
record = db.iloc[-1]
out = nt.analyse_nttestrecord(record)
nt.results_nttestrecord(out)
```

When using Spyder, select the `pyqt6_env` interpreter or kernel after installing
`spyder-kernels`.

## Tests

Run the focused Python tests from the repository root:

```bash
pytest tests
```

Return to the [manual index](README.md).
