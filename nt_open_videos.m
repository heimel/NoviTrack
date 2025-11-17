function [vidobj,video_info,available_cameras] = nt_open_videos(record)
%nt_open_videos. Open video streams for NoviTrack and reads associated triggers
%
%    [VIDOBJ,VIDEO_INFO,AVAILABLE_CAMERAS] = nt_open_videos(RECORD)
%
%    VIDOBJ is a cell list with video ojects
%    VIDEO_INJO is [n_cameras x 1 struct] with fields
%        TRIGGER_TIMES is a vector of recorded triggers per camera
%
% 2025, Alexander Heimel

params = nt_default_parameters(record);

session_path = nt_session_path(record,params);

num_cameras = length(params.nt_camera_names);

vidobj = cell(1,num_cameras);

available_cameras = [];
video_info = struct('trigger_times',[],'framerate',[],'n_frames',[],'duration',[]);

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

    video_info(i).FrameRate = vidobj{i}.FrameRate;
    video_info(i).NumFrames = vidobj{i}.NumFrames;
    video_info(i).Duration = vidobj{i}.Duration;
    video_info(i).trigger_times = nt_load_video_triggers(record,params.nt_camera_names{i},vidobj{i}.FrameRate);
    video_info(i).filename = filename;
    video_info(i).ext = ext;
end % camera i
