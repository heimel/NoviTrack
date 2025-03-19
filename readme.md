# NoviTrack README.md #

NoviTrack is a tool to track animal behavior. It can load Neurotar data files and track animal behavior 
from video recordings. It also contains some tools for using Raspberry Pi's for video recording. The 
video recording can be combined with visual stimulation. 

NoviTrack is developed and maintained by Alexander Heimel, with help of Zhiting Ren.

## Installation ##

### Experiment control or analysis PC ###

Install MATLAB.
Install repositories [heimel/InVivoTools](https://github.com/heimel/InVivoTools), 
[heimel/NoviTrack](https://github.com/heimel/NoviTrack).

After installing InVivoTools and adding the InVivoTools folder to the Matlab path, run 'load_invivotools' 
in matlab. This creates a file processparams_local.m, in which you can place local parameters overrides. 
In this file, add a line like "params.networkpathbase = 'YOUR_DATA_FOLDER';" 
where you replace YOUR_DATA_FOLDER with the root folder of your data. 


For creating FYD-session logs, install repository
[Herseninstituut/FYD_Matlab](https://github.com/Herseninstituut/FYD_Matlab). For connecting 
to the FYD-database, you need to obtain a group specific file 'nhi_fyd_XXXparms.m' with account information
from a group member, and place in a subfolder 'par' in the folder containing getFYD.m. 

For visual stimulation also install repository [heimel/NewStim3](https://github.com/heimel/NewStim3)
Check readme information on github for install information.

### Raspberry Pi for video recording ###
In shell:
```
git -clone https://github.com/heimel/NoviTrack 
```
The raspberry pi needs to be mounted to the network to be able to save the data. 
A symbolic links needs to be made such that the folder can be accessed like //SERVER/FOLDER/.


### Visual Stimulus PC ###

It is optional to use visual stimulation. For this purpose, one can
use NewStim3. Install repositories heimel/InVivoTools, heimel/NewStim3
Check readme information on github for install information.
In MATLAB:
```
NewStimInit
``` 
Edit in NewStimConfiguration
```
Remote_Comm_dir = ‘\\vs03.herseninstituut.knaw.nl\vs03-csf-1\Communication\SETUP’;
```
where SETUP should be changed to the name of the setup
If stimulus and control PC refer to the data folder in a different way, then adapt
```
Remote_Comm_localprefix = ‘’; % prefix on control PC
Remote_Comm_remoteprefix = ‘’; % prefix on stimulus PC
```




## Connecting the setup ##

Multiple connection schemes are possible. 

### Syncing pulse from Visual Stimulus PC ###

One option is that the Visual Stimulus PC gives a synchronization TTL pulse at the start of the stimulus script. In this case, add a USB2UART (USB2RS232) port to the Visual Stimulus PC. Connect the DTR and GND pins of the serial port to the center pin (usually red wire) and shield pin (usually black wire) of a female pins to BNC cable.

In Matlab, edit NewStimConfiguration, such that
```
StimSerialSerialPort = 1
NSUseInitialSerialTrigger = 1;
StimSerialScriptOut = 'COMX';  
StimSerialScriptOutPin = 'dtr';      
```
where you replace COMX by the COM port created by the USB2UART device. This can be found in Windows device manager.

On the Raspberry Pi, connect GPIO pin 17 (default setting in nt_picam_slave.py) and a GPIO GND pin to the center
pin (usually red wire) and shield pin (usually black wire) of a female pins to BNC cable.

Connect the BNC ends of the cables coming from the Visual Stimulus PC and the Raspberry Pi. If multiple 
Raspberry Pi's need to be coupled the signal can be split by BNC three-way splitters.

### Syncing pulse from third party ###

A third party can also give a TTL trigger to start the visual stimulation. Refer to NewStim3 
documentation for how to invoke NewStim3 for this purpose.



## Running an experiment ##

### Raspberry pi for video recording ###

Start video recording by opening a shell:
``` 
python NoviTrack/nt_picam_slave.py Behavior_arena
``` 
The name of the setup, in this example 'Behavior_arena', determines the folder where the raspberry pi will look for the 
acqReady file.

### Visual Stimulus PC ###

In MATLAB:
``` 
initstims
``` 
This should open a stimulus screen, and the stimulus PC will listen to changes in the file acqReady.


### Control PC ###

In MATLAB:
``` 
runexperiment
``` 
In the RunExperiment window, load or create stimulus script with StimEditor and ScriptEditor.
Click on RemoteScriptEditor, and transfer and load script to Visual stimulus PC.
``` 
nt_create_session()
``` 
Select and enter the session information in the Follow-Your-Data form and click Close. This will create a new session folder and save the associated json-file in FYD-format.

In the RunExperiment window, make sure the 'From acqReady' and 'Acquisition' checkboxes are ticked. 
Select stimulus scrip to show and click Show.


## Analyzing an experiment ##

Create a nt_database in MATLAB. This can be done by
```
experiment_db('nt')
```
and manually creating the records and saving the database. Alternatively, 
adapt create_nttestdb_233505 to collect the FYD json files and fill a MATLAB 
database (struct array) with matching record.

Press Track to mark behaviors. Check out the help by clicking on the question mark, or typing 'h'.
Markers indicating the start of a behavior are entered by typing 'm' followed by the behavior marker. 
The end of a behavior is indicated by a marker for the start of a new behavior, or by inserting 
the marker 'i' for idle. 

Press Analyse to track the animal, and subsequently run an analysis on the position and behavior
tracking.






