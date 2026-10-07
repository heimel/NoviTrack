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

Python exposes tracking data through `TrackingStream` objects. Each stream
retains its native timestamps or video-frame indices, clock identity, optional
`ClockTransform` to session reference time, coordinate system, associated
camera, capabilities, and source-specific fields. A `TrackingStreamCollection`
holds the independently sampled streams for one session. Legacy `nt_data`
structures remain supported through an adapter and continue to use their
existing `Time` values as reference time.

DeepLabCut CSV and HDF5 results are discovered from the corresponding video
stem (for example, `<video stem>DLC*.h5`) and loaded directly as independent
streams; they are not copied into `nt_tracking_data.mat`. A DLC stream stores
its unfiltered positions as `data["keypoints"]` with shape
`samples x keypoints x 2`, its confidence values as `data["likelihood"]`, and
the matching names in `metadata["keypoint_names"]`. Its native time is the
source-video frame time, `frame_indices` retains the exact DLC frame numbers,
and its clock transform maps those times to session reference time.

For a fixed arena, an overhead-camera DLC stream also stores calibrated points
as `data["keypoints_arena"]`. These have the same shape as the raw keypoints and
use the canonical arena frame: metres, origin at arena centre, x right, y up.
The raw pixel coordinates are retained unchanged. The stream metadata contains
the full spatial calibration contract and parameters, and the
`arena_position` capability indicates that calibrated points are available.
Side-camera streams are not projected onto the arena floor without a separate
calibration. Neurotar calibration is intentionally deferred because its
pixels-to-arena transform depends on the time-varying cage position and angle.

Calibrated pose streams compute movement measures once during loading. DLC
likelihood first masks unreliable samples, short internal gaps are linearly
interpolated, and each uninterrupted keypoint segment is smoothed with a
Savitzky-Golay filter before differentiation. The duration and smoothing
parameters are stored in `metadata["derived_measures"]` together with the exact
keypoint definitions and units. No interpolation, smoothing, or derivative is
performed across a long missing-data interval.

The default definitions are:

- `position_arena`: `body_center`, in m. If unavailable, NoviTrack tries a
  `com`/`center_of_mass` keypoint, then `head_center`, then the midpoint of
  `nose` and `tail_base` for older two-point tracking.
- `Speed`: magnitude of body-centre velocity, in m/s and always non-negative.
- `body_direction`: `tail_base` to `neck`, in degrees. It falls back to
  `tail_base` to `head_center`, or to `nose` for older tracking.
- `Forward_speed`: body-centre velocity projected onto body direction, in m/s;
  positive is forward and negative is backward.
- `head_direction`: `head_center` to `nose`, in degrees.
- `movement_direction`: direction of body-centre velocity, in degrees.
- `head_body_angle`: wrapped `head_direction - body_direction`, in degrees.
- `body_angular_velocity`: derivative of unwrapped body direction, in deg/s.

All directions use the canonical arena convention: right is 0 degrees,
counter-clockwise is positive, and stored directions are in `[-180, 180)`.
The legacy aliases `CoM_X`, `CoM_Y`, `alpha`, `Angular_velocity`, and
`Abs_angular_velocity` remain available to existing viewers and analyses.

When present, `DeepLabCut/<camera name>/config.yaml` in the session folder is
the authoritative source for the stream's skeleton, likelihood cutoff, marker
size, keypoint colormap, and skeleton color. `DeepLabCut/config.yaml` is accepted as a
single-model fallback, and the legacy folder name `DLC` is also recognized.
The behavior viewer uses an exact DLC frame match when available and otherwise
falls back to the nearest sample in session reference time.

## Database

Databases contain records with session information for a specific study dossier.

Databases are stored individually in mat-file in variable 'db'.

Example location: \\vs03.herseninstituut.knaw.nl\\VS03-CSF-1\\Ou\\SC\_Dopamine\\Data\_collection\\24.35.02\\nttestdb\_24.35.02.mat



## Measures

Measures contains results of analysis or tracking of one session. The struct is saved in a field for the session record in the database.

measures is array of struct with fields:

    period_of_interest = [1x2] with start and stop time of period of interest in master time

    position_tracking_available = boolean indicating whether finite paired position samples were available during Python analysis

    tracking_processing = workflow metadata for externally processed tracking.
    For DeepLabCut this records the prompt response (`ask_later`, `never`, or
    `queued`), processing state, selected model configuration, video, queue job
    identifier, manifest location, and timestamps. It does not contain tracking
    samples.

When behavioral tracking finds no position data, NoviTrack can create an atomic
JSON job manifest in the `pending` directory below
`nt_deeplabcut_queue_folder`. Available models are immediate subdirectories of
`nt_deeplabcut_projects_folder` containing a `config.yaml`. The shared manifest
is the interface to the separate GPU worker; that worker does not modify the
NoviTrack database.



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

Motion channel types are selected with `nt_motion_snippet_observables` in
`nt_default_parameters.yaml`. The default is `Speed`, `Forward_speed`,
`Abs_angular_velocity`, and `Distance_to_center`. Available channels receive the
same per-event signal, baseline, and response measures as photometry channels;
unavailable channels are skipped. Their physical units are carried over from
the selected tracking stream (for example, m/s for speed and degrees/s for
angular velocity).

Snippets are saved per session in variable 'snippets' in a mat-file 'nt_snippets.mat' in nt_session_folder(record).

Example location: \\vs03.herseninstituut.knaw.nl\\VS03-CSF-1\\Ou\\SC\_Dopamine\\Data\_collection\\24.35.02\\0115018\\0115018\_20250826\_001\\nt\_snippets.mat



## Photometry

photometry.(channel).(type) = struct with fields
   'time' [n_samples x 1] = time stamps in master time
   'signal' [n_samples x 1] = signal

Photometry data is saved per session in variable 'photometry' in mat-file 'nt_photometry.mat' in nt_photometry_folder(record).

Example location: \\vs03.herseninstituut.knaw.nl\VS03-CSF-1\Ou\SC_Dopamine\Data_collection\24.35.02\0115018\0115018_20250826_001\2025_08_26-16_18_00\nt_photometry.mat

