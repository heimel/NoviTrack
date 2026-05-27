# NoviTrack

NoviTrack is a toolkit for tracking animal behavior and analyzing related
NoviTrack experiments, including behavior videos, Neurotar data, fiber
photometry, events, snippets, and session summaries.

The Python implementation in `novitrack` is the primary development path. The
MATLAB implementation remains available in `Toolbox` for existing users and for
checking analyses against the original tools.

NoviTrack is developed and maintained by Alexander Heimel.

## Repository layout

```text
NoviTrack/
  novitrack/       Python NoviTrack package
  test_data/       Example database and expected preview outputs
  tests/           Python tests
  Toolbox/         MATLAB NoviTrack toolbox
```

Other files in the repository support acquisition computers, Raspberry Pi video
recording, documentation, and setup-specific helper scripts.

## Data paths

Both implementations expect session data to be organized below a local or
network data root. Configure this root locally:

- Python: use `processparams_local.py` on your Python path, or pass an override
  YAML file to `load_parameters`.
- MATLAB: use `processparams_local.m`, created by `load_invivotools`.

The important parameter is:

```text
networkpathbase = YOUR_DATA_FOLDER
```

Session paths are then built from database fields such as `project`, `dataset`,
`subject`, and `sessionid`.

## Python

### Installation

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

For one Python session (replace ... by actual path):

```python
import sys
sys.path.append(r"C:\Users\...\InPythoTools;C:\Users\...\NoviTrack")

import novitrack as nt
```

For persistent use in the conda environment (replace ... by actual path):

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

### Usage

From the NoviTrack repository root:

```python
import novitrack as nt

browser = nt.experiment_db()
```

This opens the database browser using `test_data/nttestdb_examples.mat` when no
filename is supplied.

To use a MATLAB-like interactive workflow in VS Code, install the Python and
Jupyter extensions, use Ctrl-Shift-P to select the `pyqt6_env` interpreter, and open the Interactive
Window with `Jupyter: Create Interactive Window`. In a fresh Interactive Window
or notebook kernel, enable Qt windows before importing `novitrack`:

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

Basic analysis usage:

```python
import novitrack as nt

db = nt.load_mat_database("test_data/nttestdb_examples.mat")
record = db.iloc[-1]
out = nt.analyse_nttestrecord(record)
nt.results_nttestrecord(out)
```

When using Spyder, select the `pyqt6_env` interpreter/kernel after installing
`spyder-kernels`.

### Tests

Run the focused Python tests from the repository root:

```bash
pytest tests
```

## MATLAB

The MATLAB implementation is in `Toolbox`. Keep this folder name, since existing
users and MATLAB conventions expect a toolbox folder.

### Installation

Install MATLAB and download these repositories:

- [heimel/InVivoTools](https://github.com/heimel/InVivoTools)
- [heimel/NoviTrack](https://github.com/heimel/NoviTrack)

After downloading InVivoTools and adding the InVivoTools folder to the MATLAB
path, run:

```matlab
load_invivotools
```

This creates `processparams_local.m`, where local parameter overrides can be
placed. For example:

```matlab
params.networkpathbase = 'YOUR_DATA_FOLDER';
```

Add `NoviTrack/Toolbox` to your MATLAB path.

For creating FYD session logs, install
[Herseninstituut/FYD_Matlab](https://github.com/Herseninstituut/FYD_Matlab).
For connecting to the FYD database, obtain the group-specific
`nhi_fyd_XXXparms.m` account file from a group member and place it in a `par`
subfolder in the folder containing `getFYD.m`.

For visual stimulation, also install
[heimel/NewStim3](https://github.com/heimel/NewStim3).

### Analyzing an experiment

Create a NoviTrack database in MATLAB:

```matlab
experiment_db('nt')
```

Then manually create records and save the database, or adapt
`create_nttestdb_233505` to collect FYD JSON files and fill a MATLAB struct-array
database.

In the database browser:

- Use `Track` to mark behaviors.
- Type `h` or click the help button for tracking help.
- Enter behavior starts by typing `m` followed by the behavior marker.
- Mark idle periods with `i`.
- Use `Analyse` to track the animal and analyze position/behavior data.

## Running experiments

### Raspberry Pi for video recording

Clone NoviTrack on the Raspberry Pi:

```bash
git clone https://github.com/heimel/NoviTrack ~/NoviTrack
```

Mount the fileserver:

```bash
~/NoviTrack/mount_fileserver
```

Make the mount script executable if needed:

```bash
chmod +x ~/NoviTrack/mount_fileserver
```

Start video recording:

```bash
python ~/NoviTrack/nt_picam_slave.py Behavior_arena
```

The setup name, here `Behavior_arena`, determines the folder where the Raspberry
Pi looks for the `acqReady` file.

### Visual stimulus PC

Visual stimulation is optional and uses NewStim3. In MATLAB:

```matlab
NewStimInit
initstims
```

Configure the remote communication directory in `NewStimConfiguration`, for
example:

```matlab
Remote_Comm_dir = '\\vs03.herseninstituut.knaw.nl\vs03-csf-1\Communication\SETUP';
```

If the stimulus and control PCs refer to the data folder differently, adapt:

```matlab
Remote_Comm_localprefix = '';
Remote_Comm_remoteprefix = '';
```

### Control PC

In MATLAB:

```matlab
runexperiment
```

In the RunExperiment window, load or create a stimulus script with StimEditor
and ScriptEditor. Use RemoteScriptEditor to transfer and load the script on the
visual stimulus PC.

Create a new NoviTrack session:

```matlab
nt_create_session()
```

Select and enter session information in the Follow-Your-Data form. This creates
a new session folder and saves the associated FYD-format JSON file.

## Synchronization

Ideally, synchronization TTL pulses are recorded by the acquisition device and
the Raspberry Pi cameras. Three pulses are recommended:

1. At the beginning of the session.
2. At the start of the experimental paradigm.
3. Before the end of the session.

These pulses make it possible to align the start, synchronize clocks, and check
for missing data.

A visual stimulus PC can also send a synchronization TTL pulse through a
USB2UART/USB2RS232 port. In NewStim3, configure:

```matlab
StimSerialSerialPort = 1;
NSUseInitialSerialTrigger = 1;
StimSerialScriptOut = 'COMX';
StimSerialScriptOutPin = 'dtr';
```

Replace `COMX` with the serial port shown in Windows Device Manager.

## More information

- [neurotar_data_explanation.md](neurotar_data_explanation.md)
- [nt_data_structures.md](nt_data_structures.md)
- [novitrack_coordinates.md](novitrack_coordinates.md)
