function [motion,time] = nt_compute_visual_motion(record)
% nt_compute_visual_motion. Computes frame by frame motion signal in movie
%
% motion = nt_compute_visual_motion(record)
%
% 2024, Alexander Heimel


params = nt_default_parameters(record);

movie_path = nt_session_path(record,params);

camera_names = {'pilefteye','pioverhead','pirighteye'};
num_cameras = length(camera_names);

vidobj = cell(1,num_cameras);

available_cameras = [];
for i = 2 %1:num_cameras
    filename = fullfile(movie_path,[record.sessionid  '_' camera_names{i} ]);
    logmsg(['Opening movie ' filename '.mp4']);
    vidobj{i} = VideoReader([filename '.mp4']);
    available_cameras = [available_cameras i]; %#ok<AGROW>

    if vidobj{i}.FrameRate~=30
        logmsg(['Framerate of ' filename '.mp4 is not 30 fps. Check to see if correctly converted. When in doubt remove mp4 file to reconvert.'])
    end
end

filename = fullfile(movie_path,[record.sessionid  '_' camera_names{2} ]);

if exist([filename '_motion.mat'],'file')
    load([filename '_motion.mat'],'orgmotion','motion','time')
else
    vid = vidobj{2};
    vid.CurrentTime = 0;

    n_frames = floor(vid.Duration);

    motion = zeros(1,n_frames);
    time = zeros(1,n_frames);
    prevtime = vid.CurrentTime;
    prevframe  = readFrame(vid);
    for i=2:n_frames
        disp([num2str(i) '  of ' num2str(n_frames)])
        newtime = i-1;
        vid.CurrentTime = newtime;
        time(i) = mean([vid.CurrentTime prevtime]);
        frame  = readFrame(vid);
        motion(i) = mean(frame(:)-prevframe(:));
        prevframe = frame;
        prevtime = newtime;
    end
    orgmotion = motion;
    %%
    motion = orgmotion;
    motion = motion - prctile(motion,5);
    motion(motion<0) = 0;
    max_motion = mean(motion)+5*std(motion);
    motion(motion>max_motion) = max_motion;

    save([filename '_motion.mat'],'orgmotion','motion','time')
end

%x = autocorrf(motion)

%figure
%plot(motion)


% calculate the autocorrelation function of A, A must be a column vector
% Author: Sheng Liu
% Email: ustc.liu@gmail.com
% Date: 7/16/2015
    % function x = autocorrf(A)
    %     % get the size of A
    %     [row,col] = size(A);
    %     if (row ~= 1 && col ~= 1)
    %         error('The input should be a vector, not a matrix!');
    %     end
    %     if row == 1
    %         A = A';
    %     end
    %     N = length(A);
    %     x = zeros(N,1);
    %     x(1) = sum(A.*A);
    %     for ii = 2:N
    %         B = circshift(A,-(ii-1));
    %         B = B(1:(N-ii+1));
    %         x(ii) = sum(B.*A(1:(N-ii+1)));
    %     end
    %     x = x/x(1);
    % end