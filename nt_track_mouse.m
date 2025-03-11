function record = nt_track_mouse(record,time_range,arena_rect,verbose)
%NT_TRACK_MOUSE tracks mouse in movie from record or filename
%
%   record = nt_track_mouse(record,[time_range],[arena_rect],[verbose])
%
% 2025, Alexander Heimel, adaptated from wc_track_mouse


if nargin<4 || isempty(verbose)
    verbose = true;
end
if nargin<3 || isempty(arena_rect)
    arena_rect = [];
end
if nargin<2 || isempty(time_range)
    time_range = [];
end

params = nt_default_parameters(record);

measures = record.measures;

% parameters
params.make_track_video = false;

% defaults
logmsg(['Tracking mouse in ' recordfilter(record)]);

vidobj = nt_open_videos(record);
vid = vidobj{params.nt_overhead_camera};


framerate = vid.FrameRate;

Frame = readFrame(vid);
s = size(Frame);


% Time range that needs to be analyzed
if isempty(time_range)
    time_range = [0 vid.Duration];
elseif vid.Duration<time_range(2)
    errormsg(['Video shorter than stimulus in ' recordfilter(record)]);
    return
end

if verbose
    figRaw = figure('Name','Raw');
    if params.make_track_video
        writerObj = VideoWriter('mousetracking1.avi');
        writerObj.FrameRate = framerate;
        open(writerObj);
    end
else
    figRaw = [];
end

% Make a background by averageing frames in bgframes
% The background is complemented so black shapes become white and can be
% substracted from each other.
bg = double(compute_movie_background(vid,time_range));
if isempty(bg)
    logmsg(['Could not compute background in ' recordfilter(record)]);
    return
end

% The actual videoanalysis part
% Runs a for loop trough all frames that need to be analysed specified by
% frameRange. For every frame, the background is substracted. Then, the
% resulting image is tresholded to have the remainig shape which is assumed
% to be the mouse. From this, the position of the mouse is calculated.
% Around this position the mean pixelvalue change is calculated that is
% used later for freeze detection.

logmsg(['Detecting mouse starting from ' num2str(time_range(1)) ' s.']);
try
    vid.CurrentTime = time_range(1);
catch me
    logmsg([me.message ' in ' recordfilter(record)]);
    return
end


n_frames = ceil((time_range(2)-time_range(1)) * framerate);
frametimes = NaN(n_frames,1);

% all_stim_ids = [1 2];
% for i=1:length(all_stim_ids)
%     stim_position = struct('stim_id',all_stim_ids(i),'com',NaN(n_frames,2));
% end

stim_position = struct('stim_id',[],'com',[]);
stim_position = stim_position([]);

position = struct('com',NaN(n_frames,2),'tailbase',NaN(n_frames,2),'nose',NaN(n_frames,2));
vidDif = NaN(n_frames,1); % for the difference per frame
Frame = [];
i = 1;

% DisableKeysForKbCheck(231); % ignore for laptop Alexander
prev_mousepos = [];
prev_stimpos = [];

start = tic();
while vid.CurrentTime < time_range(2) && hasFrame(vid)

    frametimes(i) = vid.CurrentTime;
    oldframe = Frame;
    Frame = readFrame(vid);

    if mod(i-1,round(framerate)*5)==0 % each 5 s
        duration = toc(start);
        time_analyzed = frametimes(i)-frametimes(1);
        time_to_analyze = diff(time_range);
        expected_duration = (time_to_analyze-time_analyzed)*duration/time_analyzed;
        logmsg(['Analyzed ' num2str(time_analyzed,'%0.1f') ' s of '...
            num2str(time_to_analyze,'%0.1f') ' s of movie. ' ...
            'Expected finish at: '  char(datetime('now') + seconds(expected_duration))])
    end

    if verbose
        figure(figRaw);
        gFrame = uint8(double(Frame).^params.nt_play_gamma / (255^params.nt_play_gamma) * 255);
        hImage = image(gFrame); %#ok<NASGU>
        axis image off
        hold on
    end

    cur_stim_ids = nt_which_stimuli(measures.markers,frametimes(i),params);
    n_cur_stims = length(cur_stim_ids);

    % overrule previous stimulus position by measures
    for j=1:n_cur_stims
        stim_id = cur_stim_ids(j);
        % check if new OVERHEAD position in measures
        ind_object = find(measures.object_positions(:,1)==frametimes(i) & ...
            measures.object_positions(:,5)==stim_id,1,'last');
        if ~isempty(ind_object) && measures.object_positions(ind_object,4)==params.OVERHEAD            
            ind = find(prev_stimpos(:,3)==stim_id,1);
            if ~isempty(ind)
                prev_stimpos(ind,:) = []; %#ok<AGROW>
            end
            prev_stimpos(end+1,:) = [measures.object_positions(ind_object(1:2)) stim_id]; %#ok<AGROW>
        end
    end

    [mousepos,stimpos] = nt_get_mouse_position( Frame,bg,n_cur_stims,params,figRaw,arena_rect,prev_mousepos,prev_stimpos);

    position.com(i,:) = mousepos.com;
    position.tailbase(i,:) = mousepos.tailbase;
    position.nose(i,:) = mousepos.nose;

    if all(~isnan(mousepos.com))
        prev_mousepos.com = mousepos.com;
    end
    if all(~isnan(mousepos.tailbase))
        prev_mousepos.tailbase = mousepos.tailbase;
    end
    if all(~isnan(mousepos.nose))
        prev_mousepos.nose = mousepos.nose;
    end

    prev_stimpos = stimpos;
    for j = 1:size(stimpos,1)
        stim_id = stimpos(j,3);
        ind_stim = find( [stim_position(:).stim_id] == stim_id ,1);
        if isempty(ind_stim)
            ind_stim = length(stim_position)+1;
            stim_position(ind_stim) = struct('stim_id',stim_id,'com',NaN(n_frames,2));
        end
        stim_position(ind_stim).com(i,:) = stimpos(j,1:2);
    end

    % This part defines the scope in which the difference between last
    % frame is calculated
    if any(isnan(position.com(i,:))) || i==1
        vidDif(i) = 0;
    else
        frameDif = abs(Frame - oldframe);
        params.wc_difScopex1 = max(1,round(position.com(i,1) - params.wc_difScope));
        params.wc_difScopex2 = min(s(2),round(position.com(i,1)+ params.wc_difScope));
        params.wc_difScopey1 = max(1,round(position.com(i,2) - params.wc_difScope));
        params.wc_difScopey2 = min(s(1),round(position.com(i,2)+ params.wc_difScope));
        frameDifMouse = frameDif(params.wc_difScopey1:params.wc_difScopey2,params.wc_difScopex1:params.wc_difScopex2,:);
        vidDif(i) = mean(frameDifMouse(:));
    end

    % Show the frame and already set the difscope square and dot for
    % position of mouse
    if verbose
        text(s(2)-70,s(1)-20,[num2str(vid.CurrentTime,'%0.2f') ' s'],'Color','white','horizontalalignment','right');
        drawnow
        if params.make_track_video
            frame = getframe;
            writeVideo(writerObj,frame);
        end
    end

    i = i + 1;
end

% record.measures.frametimes = frametimes;
% record.measures.position = position;
% record.measures.stim_position = stim_position;

% save tracks
session_path = nt_session_path(record,params);
filename = [ record.sessionid '_' record.condition '_' record.stimulus ...
    '_tracks_' char(datetime('now','format','yyyyMMddHHmmss')) '.mat'];
filename = fullfile(session_path,filename);
save(filename,'frametimes','position','stim_position')
logmsg(['Saved tracking data in ' filename]);

if params.make_track_video
    close(writerObj);
end

clear vidobj


logmsg('You might want to run nt_detect_freezing')
