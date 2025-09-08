# Data structures

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

For each record, the function nt\_compute\_event\_measures, computes several measures using these snippets, e.g. measures.event.(event\_type).(channel\_type).snippet\_mean = snippet\_mean. The structure event is saved in the session measures.

Snippets are saved per session in variable 'snippets' in a mat-file 'nt_snippets.mat' in nt_session_folder(record).

Example location: \\vs03.herseninstituut.knaw.nl\\VS03-CSF-1\\Ou\\SC\_Dopamine\\Data\_collection\\24.35.02\\0115018\\0115018\_20250826\_001\\nt\_snippets.mat



## Photometry

photometry.(channel).(type) = struct with fields
   'time' [n_samples x 1] = time stamps in master time
   'signal' [n_samples x 1] = signal

Photometry data is saved per session in variable 'photometry' in mat-file 'nt_photometry.mat' in nt_photometry_folder(record).

Example location: \\vs03.herseninstituut.knaw.nl\VS03-CSF-1\Ou\SC_Dopamine\Data_collection\24.35.02\0115018\0115018_20250826_001\2025_08_26-16_18_00\nt_photometry.mat

