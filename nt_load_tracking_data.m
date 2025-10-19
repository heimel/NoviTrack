function [nt_data,trigger_times] = nt_load_tracking_data(record,recompute)
% nt_load_tracking_data. Loads tracking data into NoviTrack format
%
%   [NT_DATA,TRIGGER_TIMES] = nt_load_tracking_data(RECORD,VID,RECOMPUTE = false)
%
%   returns NT_DATA = struct with fields
%             Time: [n_samples×1 double]  (s)
%                X: [n_samples×1 double]  tip of nose, X 
%                Y: [n_samples×1 double]  tip of nose, Y 
%            CoM_X: [n_samples×1 double]  center of mass, X 
%            CoM_Y: [n_samples×1 double]  center of mass, Y 
%       tailbase_X: [n_samples×1 double]  tailbase, X 
%       tailbase_Y: [n_samples×1 double]  tailbase, Y 
%    	     alpha: [n_samples×1 double]  deg, angle between mouse longitudonal axis and arena y-axis, NOT IMPLEMENTED
%  Derived measures
%    Forward_speed: [n_samples×1 double]  NOT IMPLEMENTED
% Angular_velocity: [n_samples×1 double]  deg/s, change in alpha
%  Object_distance: [n_samples×1 double]  NOT IMPLEMENTED
%  Distance_to_center: [n_samples×1 double]  sqrt(CoM_X^2 + CoM_Y^2)
%      Coordinates: params.ARENA,.NEUROTAR,.CAMERA,.OVERHEAD coordinate system of X,Y data
%
%   TRIGGER_TIMES = [1xn_triggers] vector of trigger times in reference of
%   NT_DATA.Time
%
%   If exists and not RECOMPUTE, then loads data from nt_tracking_data.mat.
%   Otherwise checks for Neurotar, nt_track_mouse or DLC tracking data.
%
% 2025, Alexander Heimel

nt_data = [];


params = nt_default_parameters(record);

if nargin<2 || isempty(recompute)
    recompute = params.nt_recompute_tracking_data;
end

[folder,exists] = nt_session_path(record);
if ~exists
    logmsg(['Folder ' folder ' does not exist.'])
    if isfield(record.measures,'trigger_times')
        trigger_times = record.measures.trigger_times;
    else
        trigger_times = [];
    end
    return
end

filename = fullfile(folder,'nt_tracking_data.mat');



if ~recompute && exist(filename,'file') 
    logmsg(['Loading precomputed tracking data. To recompute set params.nt_recompute_tracking_data = true or delete ''' filename ''''] )
    load(filename,'nt_data');
    return
end

nt_data = nt_load_neurotar_data(record);
if ~isempty(nt_data)
    logmsg('Not yet reading in all triggers. Assuming one trigger broadcast by Neurotar at time 0.');
    trigger_times = 0;
    return
end

if ~isfield(record.measures,'video_info')
    logmsg('Track behavior first');
    return
end

if isempty(nt_data) % Blomer tracking
    nt_data = nt_load_mouse_tracks(record); % does not set Time and derived variables
end
if isempty(nt_data) % DLC tracking
     nt_data = nt_load_DLC_data(record); % does not set Time and derived variables
end
if isempty(nt_data) % Noldus tracking
     nt_data = nt_load_noldus_tracking(record); % 
end

% Get time and trigger from overhead video
video_info = record.measures.video_info(params.nt_overhead_camera);

if ~isfield(nt_data,'Time') || isempty(nt_data.Time)
    nt_data.Time = extract_frametimes(video_info);
end

nt_data.Time = nt_data.Time - video_info.trigger_times(1);
trigger_times = video_info.trigger_times - video_info.trigger_times(1);

% Filter tracking data 
filter_width = params.nt_pose_temporal_filter_width;

if isfield(nt_data,'X')
    nt_data.X = medfilt1(nt_data.X,filter_width,'omitnan');
    nt_data.Y = medfilt1(nt_data.Y,filter_width,'omitnan');
end
if isfield(nt_data,'CoM_X')
    nt_data.CoM_X = medfilt1(nt_data.CoM_X,filter_width,'omitnan');
    nt_data.CoM_Y = medfilt1(nt_data.CoM_Y,filter_width,'omitnan');
end
if isfield(nt_data,'tailbase_X')
    nt_data.tailbase_X = medfilt1(nt_data.tailbase_X,filter_width,'omitnan');
    nt_data.tailbase_Y = medfilt1(nt_data.tailbase_Y,filter_width,'omitnan');
end



%% Compute speed and add fields to nt_data as necessary
if ~isfield(nt_data,'Speed')
    if isfield(nt_data,'CoM_X') && isfield(nt_data,'Time')
        dt = mean(diff(nt_data.Time));
        overhead_mm_per_pixel = 0.5; % coarse estimate.
        nt_data.Speed = NaN(size(nt_data.CoM_X));
        nt_data.Speed(1:end-1) = sqrt(diff(nt_data.CoM_X).^2 + diff(nt_data.CoM_Y).^2) / dt * overhead_mm_per_pixel /1000; % in m/s
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
    if any(~isnan(nt_data.X)) && any(~isnan(nt_data.CoM_X))
        vx = nt_data.X - nt_data.CoM_X;
        vy = nt_data.Y - nt_data.CoM_Y;
        nt_data.alpha = angle(vy + 1i*vx)/pi*180; % deg, angle with y-axis, clockwise positive
    end
end
if ~isfield(nt_data,'Forward_speed')
    nt_data.Forward_speed = NaN(size(nt_data.Time));
end
if ~isfield(nt_data,'Angular_velocity') % deg/s
    nt_data.Angular_velocity = NaN(size(nt_data.Time));
    if any(~isnan(nt_data.alpha))
        dt = mean(diff(nt_data.Time)); 
        nt_data.Angular_velocity(2:end) = angle(exp(1i*(nt_data.alpha(2:end)-nt_data.alpha(1:end-1))/180*pi)) / dt;
        nt_data.Angular_velocity = medfilt1(nt_data.Angular_velocity,filter_width,'omitnan');
    end
end
if ~isfield(nt_data,'Abs_angular_velocity') % deg/s
    nt_data.Abs_angular_velocity = NaN(size(nt_data.Time));
    if any(~isnan(nt_data.Angular_velocity))
        nt_data.Abs_angular_velocity = abs(nt_data.Angular_velocity);
    end
end
if ~isfield(nt_data,'Distance_to_center')
    nt_data.Object_distance = NaN(size(nt_data.Time));

    nt_data.Distance_to_center = sqrt(nt_data.CoM_X.^2 + nt_data.CoM_Y.^2) ; 

end

if ~isfield(nt_data,'Object_distance')
    nt_data.Object_distance = NaN(size(nt_data.Time));
end

% Save data
save(filename,'nt_data');