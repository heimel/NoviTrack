# MATLAB installation and usage

The MATLAB implementation is in `Toolbox`. Keep this folder name, since existing
users and MATLAB conventions expect a toolbox folder.

## Installation

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

See [Data paths and local configuration](data_paths.md) for more information
about configuring the data root.

## Analyzing an experiment

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
- Use `Analyse` to track the animal and analyze position and behavior data.

Return to the [manual index](README.md).
