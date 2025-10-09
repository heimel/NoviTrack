function nt_data = nt_load_mouse_tracks(record)
%nt_load_mouse_tracks. Loads results from nt_track_mouse
%
%    nt_data = nt_load_mouse_tracks(record)
%
% 2025, Alexander Heimel

params = nt_default_parameters(record);

nt_data = [];
session_path = nt_session_path(record,params);
filename = [ record.sessionid '_' record.condition '_' record.stimulus ...
    '_tracks_*.mat'];
filename = fullfile(session_path,filename);
d = dir(filename);
if isempty(d)
    logmsg(['Cannot find tracking data for ' recordfilter(record)]);
    return
end
if length(d)>1
    logmsg(['Taking latest of multiple files with tracking data for ' recordfilter(record) ]);
end
%load(fullfile(session_path,d(end).name),'frametimes','position','stim_position');
load(fullfile(session_path,d(end).name),'position','stim_position');

%nt_data.Time = frametimes;

nt_data.X = position.nose(:,1);
nt_data.Y = position.nose(:,2);
nt_data.CoM_X = position.com(:,1);
nt_data.CoM_Y = position.com(:,2);
nt_data.tailbase_X = position.tailbase(:,1);
nt_data.tailbase_Y = position.tailbase(:,2);



for i=1:length(stim_position)
    if stim_position(i).stim_id==1
        basefield = 'Object_';
    else
        basefield = ['Object' num2str(stim_position(i).stim_id) '_'];
    end
    nt_data.([basefield 'X']) = stim_position(i).com(:,1);
    nt_data.([basefield 'Y']) = stim_position(i).com(:,2);
end

% % filter
% nt_data.X = medfilt1(nt_data.X,5,'omitnan');
% nt_data.Y = medfilt1(nt_data.Y,5,'omitnan');
% nt_data.CoM_X = medfilt1(nt_data.CoM_X,5,'omitnan');
% nt_data.CoM_Y = medfilt1(nt_data.CoM_Y,5,'omitnan');
% nt_data.tailbase_X = medfilt1(nt_data.tailbase_X,5,'omitnan');
% nt_data.tailbase_Y = medfilt1(nt_data.tailbase_Y,5,'omitnan');

% dt = mean(diff(frametimes));
% overhead_mm_per_pixel = 0.5; % coarse estimate. 
% 
% nt_data.Speed = NaN(size(nt_data.CoM_X));
% nt_data.Speed(1:end-1) = sqrt(diff(nt_data.CoM_X).^2 + diff(nt_data.CoM_Y).^2) / dt * overhead_mm_per_pixel; 

logmsg('Loaded mouse tracks.')

% Still to implement
% nt_data.alpha = NaN(size(nt_data.X));
% nt_data.Forward_speed = NaN(size(nt_data.X));
% nt_data.Angular_velocity = NaN(size(nt_data.X)); 
% nt_data.Since_track_start = NaN(size(nt_data.X));
% nt_data.Distance_to_wall = NaN(size(nt_data.X));

