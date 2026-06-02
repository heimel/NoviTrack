# Synchronization

Ideally, synchronization TTL pulses are recorded by the acquisition device and
the Raspberry Pi cameras. Three pulses are recommended:

1. At the beginning of the session.
2. At the start of the experimental paradigm.
3. Before the end of the session.

These pulses make it possible to align the start, synchronize clocks, and check
for missing data.

A visual stimulus PC can also send a synchronization TTL pulse through a
USB2UART or USB2RS232 port. In NewStim3, configure:

```matlab
StimSerialSerialPort = 1;
NSUseInitialSerialTrigger = 1;
StimSerialScriptOut = 'COMX';
StimSerialScriptOutPin = 'dtr';
```

Replace `COMX` with the serial port shown in Windows Device Manager.

For more information about temporal coordinate systems, see
[NoviTrack coordinates](novitrack_coordinates.md).

Return to the [manual index](README.md).
