function [nt_data,trigger_times] = nt_load_tracking_data(record,recompute)
% nt_load_tracking_data. Loads tracking data into NoviTrack format
%
%   [NT_DATA,TRIGGER_TIMES] = nt_load_tracking_data(RECORD,VID,RECOMPUTE = false)
%
%   returns NT_DATA = struct with fields
%             Time: [n_samples×1 double]  in seconds
%                X: [n_samples×1 double]  tip of nose, X
%                Y: [n_samples×1 double]  tip of nose, Y
%            CoM_X: [n_samples×1 double]  center of mass, X
%            CoM_Y: [n_samples×1 double]  center of mass, Y
%       tailbase_X: [n_samples×1 double]  tailbase, X
%       tailbase_Y: [n_samples×1 double]  tailbase, Y
%    	     alpha: [n_samples×1 double]
%    Forward_speed: [n_samples×1 double]
% Angular_velocity: [n_samples×1 double]
%  Object_distance: 
%
%   TRIGGER_TIMES = [1xn_triggers] vector of trigger times in reference of
%   NT_DATA.Time
%
%   If exists and not RECOMPUTE, then loads data from nt_tracking_data.mat.
%   Otherwise checks for Neurotar, nt_track_mouse or DLC tracking data.
%
% 2025, Alexander Heimel

if nargin<2 || isempty(recompute)
    recompute = false;
end

folder = nt_session_path(record);
filename = fullfile(folder,'nt_tracking_data.mat');

params = nt_default_parameters(record);

if ~recompute && exist(filename,'file') 
    load(filename,'nt_data');
    return
end

nt_data = nt_load_neurotar_data(record);
if ~isempty(nt_data)
    logmsg('Not yet reading in all triggers. Assuming one trigger broadcast by Neurotar at time 0.');
    trigger_times = 0;
    return
end

if isempty(nt_data)
    nt_data = nt_load_mouse_tracks(record); % does not set Time and derived variables
end
if isempty(nt_data)
     nt_data = nt_load_DLC_data(record); % does not set Time and derived variables
end

% Get time and trigger from overhead video
video_info = record.measures.video_info(params.nt_overhead_camera);
nt_data.Time = extract_frametimes(video_info) - video_info.trigger_times(1);
trigger_times = video_info.trigger_times - video_info.trigger_times(1);

%% Compute speed and add fields to nt_data as necessary
if ~isfield(nt_data,'Speed')
    if isfield(nt_data,'CoM_X') && isfield(nt_data,'Time')
        dt = mean(diff(nt_data.Time));
        overhead_mm_per_pixel = 0.5; % coarse estimate.
        nt_data.Speed = NaN(size(nt_data.CoM_X));
        nt_data.Speed(1:end-1) = sqrt(diff(nt_data.CoM_X).^2 + diff(nt_data.CoM_Y).^2) / dt * overhead_mm_per_pixel;
    else
        nt_data.Speed = NaN(size(nt_data.Time));
    end
end
if ~isfield(nt_data,'X') % nose
    nt_data.X = NaN(size(nt_data.Time));
    nt_data.Y = NaN(size(nt_data.Time));
end
if ~isfield(nt_data,'CoM_X')
    nt_data.CoM_X = NaN(size(nt_data.Time));
    nt_data.CoM_Y = NaN(size(nt_data.Time));
end
if ~isfield(nt_data,'tailbase_X')
    nt_data.tailbase_X = NaN(size(nt_data.Time));
    nt_data.tailbase_Y = NaN(size(nt_data.Time));
end
if ~isfield(nt_data,'alpha')
    nt_data.alpha = NaN(size(nt_data.Time));
end
if ~isfield(nt_data,'Forward_speed')
    nt_data.Forward_speed = NaN(size(nt_data.Time));
end
if ~isfield(nt_data,'Angular_velocity')
    nt_data.Angular_velocity = NaN(size(nt_data.Time));
end
if ~isfield(nt_data,'Object_distance')
    nt_data.Object_distance = NaN(size(nt_data.Time));
end

% Save data
save(filename,'nt_data');