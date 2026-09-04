# Data structures

## Tracking data

Per-session tracking data are stored in `nt_tracking_data.mat` as the MATLAB
struct `nt_data`. This is the shared interchange and cache format for the
MATLAB and Python implementations. Python writes a MATLAB v5 compatible file;
the physical MAT-file encoding does not need to be byte-identical between the
two implementations.

`nt_data.Time` is an n-sample vector in seconds in master time. Spatial sample
vectors (`X`, `Y`, `CoM_X`, `CoM_Y`, `tailbase_X`, and `tailbase_Y`) have the
same length. Missing measurements are represented by `NaN`. `Coordinates`
identifies their coordinate system. Derived vectors include `Speed`,
`Forward_speed`, `alpha`, `Angular_velocity`, `Abs_angular_velocity`,
`Distance_to_center`, and `Object_distance`.

New files may contain the scalar `nt_data.schema_version`. Version 1 describes
the fields above. Files without this field are legacy version 1 files and must
remain readable. Trigger times are kept in the session record rather than in
the tracking cache.

## Database

Databases contain records with session information for a specific study dossier.

Databases are stored individually in mat-file in variable 'db'.

Example location: \\vs03.herseninstituut.knaw.nl\\VS03-CSF-1\\Ou\\SC\_Dopamine\\Data\_collection\\24.35.02\\nttestdb\_24.35.02.mat



## Measures

Measures contains results of analysis or tracking of one session. The struct is saved in a field for the session record in the database.

measures is array of struct with fields:

    period_of_interest = [1x2] with start and stop time of period of interest in master time



## Snippets

Snippets contain peri-event measurements for different channel types for all events. Channel\_type can be for example motion information (e.g. 'forward\_speed') or photometry data (e.g. 'Channel1\_410').

It is made by functions nt\_make\_XXX\_snippets, which use measures.snippets\_tbins as tbins and measures.markers as events.

snippets is a struct with fields:

    data.(channel\_type) = \[n\_events x n\_bins\_per\_snippet]
    baseline\_std.(channel\_type) = \[n\_events x 1] with median pre-event std over all snippets of one channel\_type.
    units = string, e.g. "m/s", "z-scored"  (not implemented yet)
    zscored = boolean, indicating if the snippets are z-score by the snippet baseline mean and std. deviation over all snippets. (not implemented yet)
    tbins = \[1 x n\_bins\_per\_snippet] (not implemented yet)

For each record, the function nt\_compute\_event\_measures computes several measures using these snippets, e.g. `measures.event.(event_type).(channel_type).snippet_mean = snippet_mean`. Event occurrence metadata is stored once per event type. `measures.event.(event_type).duration` is an array aligned with the event rows and with each channel's `event_mean`. Each `measures.event.(event_type).parameters.(parameter_name)` array has the same alignment when values vary between events, but is stored as a one-element array when the parameter is constant across all events. The `parameters` and `duration` names are reserved at the event-type level. The structure event is saved in the session measures.

Snippets are saved per session in variable 'snippets' in a mat-file 'nt_snippets.mat' in nt_session_folder(record).

Example location: \\vs03.herseninstituut.knaw.nl\\VS03-CSF-1\\Ou\\SC\_Dopamine\\Data\_collection\\24.35.02\\0115018\\0115018\_20250826\_001\\nt\_snippets.mat



## Photometry

photometry.(channel).(type) = struct with fields
   'time' [n_samples x 1] = time stamps in master time
   'signal' [n_samples x 1] = signal

Photometry data is saved per session in variable 'photometry' in mat-file 'nt_photometry.mat' in nt_photometry_folder(record).

Example location: \\vs03.herseninstituut.knaw.nl\VS03-CSF-1\Ou\SC_Dopamine\Data_collection\24.35.02\0115018\0115018_20250826_001\2025_08_26-16_18_00\nt_photometry.mat

