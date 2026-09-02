# RWD events and parameters

NoviTrack imports RWD event transitions from `Events.csv` when **RWD log** is
selected in the marker importer. The file is located in the RWD photometry
folder and normally contains these columns:

```text
TimeStamp,Name,State
```

`TimeStamp` is expressed in milliseconds. `Name` identifies an RWD input such
as `Input1` or `Input3`, and `State` contains its digital state. NoviTrack
combines matching state transitions into events and converts their timestamps
to the experiment's master-time seconds.

## Optional Parameters.csv

An optional `Parameters.csv` in the same folder can describe how inputs should
be interpreted and attach settings to imported markers. Its required columns
are:

```text
TimeStamp,Input,Parameter,Value
0,Input1,type,sync
0,Input4,type,ignore
0,Input3,type,opto
0,Input3,wavelength_nm,1000
0,Input3,frequency,0
395442.042,Input3,frequency,5
1610625.724,Input3,frequency,10
```

The columns have the following meanings:

- `TimeStamp`: time in RWD milliseconds, using the same clock as `Events.csv`.
- `Input`: input to which the setting applies, for example `Input3`.
- `Parameter`: the parameter name stored in the marker's `parameters`
  dictionary. Names are case-insensitive and are normalized to lowercase.
- `Value`: a numeric or text value. Numeric values are imported as numbers;
  other values remain strings.

Each row changes one parameter from that timestamp onward. The value remains
active for subsequent events on the same input until another row changes that
parameter. A change at exactly the event timestamp applies to that event.
Parameters are tracked independently, so changing `frequency` does not clear
an earlier wavelength value.

For example, the rows above give Input3 a frequency of 0 Hz initially, 5 Hz
from 395442.042 ms, and 10 Hz from 1610625.724 ms. The applicable frequency
and wavelength are added to every subsequent Input3 onset marker.

## The type parameter

`type` controls how NoviTrack interprets an input:

- `ignore` (or numeric `0`) skips events from that input.
- `opto` (or numeric `1`) creates separate `opto_on` and `opto_off` markers.
- `sync` uses the input for clock synchronization but does not create markers.

The `type` setting itself is also retained in the onset marker's `parameters`
dictionary. Other type values are treated as ordinary RWD events. Input1
defaults to `sync`, even when `Parameters.csv` is absent or has no Input1 type
row. Input3 similarly defaults to `opto`; other inputs default to ordinary
events. Declaring `0,Input1,type,sync` is therefore recommended for clarity but
is not required.

Optogenetic marker parameters use NoviTrack's normal unit convention. Thus
`frequency` is in Hz, `pulse_width` is in seconds, and `power` is in watts.
For convenience, wavelength is written as `wavelength_nm` in `Parameters.csv`;
the importer converts it to the internal `wavelength` parameter in metres.
`wavelength_nm` and spellings such as `Wavelength_nm` are equivalent. Unknown
`frequency`, `pulse_width`, and `power` values remain `NaN` unless the parameter
file supplies them.
