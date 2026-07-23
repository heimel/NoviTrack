# Synchronization

Ideally, synchronization TTL pulses are recorded by the acquisition device and
the Raspberry Pi cameras. Three or more pulses are recommended. Ideally, they should be 
spaced over the time of the session. A possible scheme is:

1. At the beginning of the session.
2. At the start of the experimental paradigm.
3. Before the end of the session.

These pulses make it possible to align the start, synchronize clocks, and check
for missing data.

## Synchronization master

Only one device can be the synchronization master. Typically, this a PC with a USB2UART device connected. 

MATLAB can be used to generate synchronization triggers. Initialize the serial port by
```matlab
s = serialport("COM5",9600,"timeout",5)
```
where COM5 is the com-port of the Serial2UART and can also be another number.

To create a trigger: 
```matlab
send_ttl_over_serial(s)`
```

A visual stimulus PC can also send a synchronization TTL pulse through a
USB2UART or USB2RS232 port. In NewStim3, configure:

```matlab
StimSerialSerialPort = 1;
NSUseInitialSerialTrigger = 1;
StimSerialScriptOut = 'COMX';
StimSerialScriptOutPin = 'dtr';
```

Replace `COMX` with the serial port shown in Windows Device Manager.
When visual stimuli start, a trigger is sent at the start of each stimulus script.

## Synchronization slaves

All other connected recording and imaging devices should either be triggered or record the timing of the synchronization triggers. They are not allowed to send triggers on the synchronization channel. Example devices are the video Raspberry Pi's and the fiber photometer.


# Temporal coordinate transformations

For more information about temporal coordinate systems, see
[NoviTrack coordinates](novitrack_coordinates.md).

Return to the [manual index](README.md).
