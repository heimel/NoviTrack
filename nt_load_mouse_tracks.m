function nt_data = nt_load_mouse_tracks(record)
%nt_load_mouse_tracks. Loads results from nt_track_mouse (Blomer analysis)
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
    return
end
if length(d)>1
    logmsg(['Taking latest of multiple files with tracking data for ' recordfilter(record) ]);
end

load(fullfile(session_path,d(end).name),'position','stim_position');

nt_data.X = position.nose(:,1);
nt_data.Y = position.nose(:,2);
nt_data.CoM_X = position.com(:,1);
nt_data.CoM_Y = position.com(:,2);
nt_data.tailbase_X = position.tailbase(:,1);
nt_data.tailbase_Y = position.tailbase(:,2);
nt_data.Coordinates = params.OVERHEAD;

for i=1:length(stim_position)
    if stim_position(i).stim_id==1
        basefield = 'Object_';
    else
        basefield = ['Object' num2str(stim_position(i).stim_id) '_'];
    end
    nt_data.([basefield 'X']) = stim_position(i).com(:,1);
    nt_data.([basefield 'Y']) = stim_position(i).com(:,2);
end

logmsg('Loaded mouse tracks.')

