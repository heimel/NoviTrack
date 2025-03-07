function [vidobj,trigger_times,available_cameras] = nt_open_videos(record,time)
%nt_open_videos. Open video streams for NoviTrack and reads associated triggers
%
%    [VIDOBJ,TRIGGER_TIMES] = nt_open_videos(RECORD,[TIME])
%
%    VIDOBJ is a cell list with video ojects
%    TRIGGER_TIMES is a cell list of recorded triggers per camera
%    if TIME is given, then current time for videos will be aligned to this
%    time, using the triggers
%
% 2025, Alexander Heimel

if nargin<2 || isempty(time)
    time = [];
end

params = nt_default_parameters(record);

session_path = nt_session_path(record,params);

num_cameras = length(params.nt_camera_names);

vidobj = cell(1,num_cameras);

available_cameras = [];
trigger_times = cell(num_cameras,1);
for i = 1:num_cameras

    filename = fullfile(session_path,[record.sessionid '_' record.condition '_' record.stimulus '_' params.nt_camera_names{i} ]);
    d = dir( [filename '.*'] );
    if isempty(d)
        filename = fullfile(session_path,[record.sessionid  '_' params.nt_camera_names{i} ]);
    end

    if ~exist([filename '.mp4'],'file') && ~exist([filename '.MP4'],'file') && ~exist([filename '.h264'],'file')
        logmsg(['Cannot find movie '  filename ]);
        vidobj{i} = struct('FrameRate',30,'Width',params.overhead_camera_width,'Height',params.overhead_camera_height);
        continue
    end
    if ~exist([filename '.mp4'],'file') && ~exist([filename '.MP4'],'file') 
        logmsg(['Converting movie '  filename '.h264 to mp4']);
        system(['MP4Box -add "' filename '.h264:fps=30" -fps original -new "' filename '.mp4"'])
    end
    if exist([filename '.mp4'],'file')
        ext = '.mp4';
    elseif exist([filename '.MP4'],'file')
        ext = '.MP4';
    end

    logmsg(['Opening movie ' filename ext]);
    vidobj{i} = VideoReader([filename ext]);
    available_cameras = [available_cameras i]; %#ok<AGROW>

    if vidobj{i}.FrameRate~=30
        logmsg(['Framerate of ' filename '.mp4 is not 30 fps. Check to see if correctly converted. When in doubt remove mp4 file to reconvert.'])
    end

    if length(trigger_times)<i || isempty(trigger_times{i})
        trigger_filename = [filename '_triggers.csv'];
        if ~exist(trigger_filename,'file')
            logmsg(['Cannot find trigger file ' trigger_filename '. Setting trigger at start.']);
            trigger_times{i} = 1 / vidobj{i}.FrameRate; % set trigger on first frame
        else
            data = readmatrix(trigger_filename, 'OutputType', 'double', 'NumHeaderLines', 1);
            if size(data,2)==1 % old data from before 2023-05-25
                trigger_times{i} = data / vidobj{i}.FrameRate;
            else % data from after 2023-05-25
                trigger_times{i} = data(2:end,3);
            end
        end
    end
end % camera i

if ~isempty(time)
    % align videos
    for c = available_cameras
        vidobj{c}.CurrentTime = trigger_times{c}(1) + time * params.picamera_time_multiplier;
    end
end