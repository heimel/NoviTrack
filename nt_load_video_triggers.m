function [triggers,events] = nt_load_video_triggers(record,camera_name,framerate)
%nt_load_video_triggers. Loads triggers file from raspberry pi videos
%
%   [TRIGGERS,EVENTS] = nt_load_video_triggers(RECORD,CAMERA_NAME,FRAMERATE=30)
%        TRIGGERS in sconds is on raspberry clock
%        EVENTS is table with fields: time, code, duration
%
% 2025, Alexander Heimel

if nargin<3 || isempty(framerate)
    framerate = 30;
end

params = nt_default_parameters(record);

session_path = nt_session_path(record,params);

filename = fullfile(session_path,[record.sessionid '_' record.condition '_' record.stimulus '_' camera_name ]);
d = dir( [filename '.*'] );
if isempty(d)
    filename = fullfile(session_path,[record.sessionid  '_' camera_name ]);
end

trigger_filename = [filename '_triggers.csv'];
if ~exist(trigger_filename,'file')
    logmsg(['Cannot find trigger file ' trigger_filename '. Setting trigger after first frame.']);
    triggers = 1 / framerate; % set trigger on second frame (was a mistake, would have been better to put on first)
else
    data = readmatrix(trigger_filename, 'OutputType', 'double', 'NumHeaderLines', 1);
    if size(data,2)==1 % old data from before 2023-05-25
        triggers = data / framerate;
    else % data from after 2023-05-25
        triggers = data(2:end,3);
    end

    % Create events table
    time = data(:,3);
    code = ["start";repmat("trigger1",size(data,1)-1,1)];
    duration = repmat(0.001,size(data,1),1);
    events = table(time,code,duration);
end
