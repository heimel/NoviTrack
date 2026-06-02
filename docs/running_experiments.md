# Running experiments

## Raspberry Pi for video recording

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

## Visual stimulus PC

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

## Control PC

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

See [Synchronization](synchronization.md) for guidance on TTL pulses.

Return to the [manual index](README.md).
