# Python installation and usage

The Python implementation in `novitrack` is the primary NoviTrack development
path.

Channel-to-fiber mappings can be set in a record's comment, for example
`channel1=fiber1,channel2=fiber2`. To exclude an unconnected channel, use
`channel1=fiber1,channel2=not connected`. The values `none`, `disconnected`, and
`nc` are also accepted, regardless of capitalization. Unspecified channels
keep the default mapping (`channelX=fiberX`). Reanalyze the record after changing
its comment to update the analysis and results. This also applies to MATLAB.

## Installation

Create a dedicated environment with Python 3.12 and install all dependencies in
one transaction from conda-forge:

```powershell
conda create -n novitrack --override-channels -c conda-forge -y `
    python=3.12 pyqt6 pandas scipy matplotlib statsmodels pytest `
    openpyxl nptdms pyqtgraph opencv ffmpeg pytables `
    spyder-kernels jupyter ipykernel pyyaml
conda activate novitrack
```

`--override-channels` prevents packages from the default Anaconda channels from
being mixed with conda-forge packages. This is particularly important for
compiled packages such as NumPy, OpenCV, PyTables/HDF5, FFmpeg, and Qt. Install
future compiled dependencies from conda-forge as well, preferably together in
one conda command rather than with `pip`.

FFmpeg is used to remux raw Raspberry Pi `.h264` recordings automatically to
seekable `.mp4` files without re-encoding them. If MP4Box from GPAC is already
installed for the MATLAB version, NoviTrack can use that as a fallback.

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
sys.path.extend([
    r"C:\Users\...\InPythoTools",
    r"C:\Users\...\NoviTrack",
])

import novitrack as nt
```

For persistent use limited to the NoviTrack conda environment, replace `...`
with the actual path:

```powershell
conda activate novitrack
conda env config vars set PYTHONPATH="C:\Users\...\InPythoTools;C:\Users\...\NoviTrack"
conda deactivate
conda activate novitrack
```

Alternatively, set `PYTHONPATH` as a Windows user environment variable. This
makes the repositories available to Python in all terminals and environments
for that Windows account:

1. Open the Start menu and search for **Edit environment variables for your
   account**.
2. Under **User variables**, create `PYTHONPATH`, or edit it if it already
   exists.
3. Add both repository folders, separated by a semicolon:

   ```text
   C:\Users\...\InPythoTools;C:\Users\...\NoviTrack
   ```

   Preserve any existing entries by appending the two folders instead of
   replacing the current value.
4. Restart open terminals, VS Code, Spyder, and other Python applications so
   they receive the updated environment variable.

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
`Python: Select Interpreter`, and choose `novitrack`. Then create a Jupyter
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

db = nt.load_mat_database()
record = db.iloc[-1]
out = nt.analyse_nttestrecord(record)
nt.results_nttestrecord(out)
```

With no filename, `load_mat_database()` loads the same bundled example database
as `experiment_db()`. Pass a path to load a different database.

When using Spyder, select the `novitrack` interpreter or kernel after installing
`spyder-kernels`.

## Tests

Run the focused Python tests from the repository root:

```bash
pytest tests
```

Return to the [manual index](README.md).
