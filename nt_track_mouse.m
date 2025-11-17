function [record,stat] = nt_track_mouse(record,time_range,verbose)
%NT_TRACK_MOUSE tracks mouse in movie from record or filename
%
%   [RECORD,STAT] = nt_track_mouse(record,[time_range],[verbose=true])
%
%      STAT contains some info on mouse detection
%
% 2025, Alexander Heimel, adaptated from wc_track_mouse


if nargin<3 || isempty(verbose)
    verbose = true;
end
if nargin<2 || isempty(time_range)
    time_range = [];
end

params = nt_default_parameters(record);

measures = record.measures;



if params.nt_constrain_to_arena 
    mask = nt_arena_mask(record);
else 
    mask = [];
end

% defaults
logmsg(['Tracking mouse in ' recordfilter(record)]);

vidobj = nt_open_videos(record);
vid = vidobj{params.nt_overhead_camera};

if  ~isa(vid,'VideoReader')
    logmsg(['Could not load the overhead video, and therefore cannot track ' recordfilter(record)])
    stat = [];
    return
end

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


% Make a background by averageing frames in bgframes
% The background is complemented so black shapes become white and can be
% substracted from each other.
[~,root] = fileparts(vid.Name);
bg_filename = fullfile(vid.Path,[root '_bg.mat']);
if exist(bg_filename,'file') && ~params.nt_recompute_background
    load(bg_filename,'bg');
else
    bg = compute_movie_background(vid,[]); % removed time_range
    if ~isempty(bg)
        save(bg_filename,'bg');
        logmsg(['Wrote background to ' bg_filename])
    end    
end
bg = double(bg);

if isempty(bg)
    logmsg(['Could not compute background in ' recordfilter(record)]);
    return
end

%% Setup video image for display
if verbose
    figure('Name','Raw');
    handles.video = axes();
    handles.image = image(handles.video,uint8(bg)); 

    if params.overhead_camera_rotated
        set(handles.video,'ydir','normal');
        set(handles.video,'xdir','reverse');
    end
    axis image off
    hold on

    % set placeholder markers
    handles.clock = text(handles.video,5,5,[num2str(vid.CurrentTime,'%0.2f') ' s'],...
        'Color','white','horizontalalignment','right','verticalalignment','bottom');
    for i = 1:10
        handles.stim(i) = text(NaN,NaN,num2str(i),...
            'HorizontalAlignment','Center','Color',[1 1 1]);
    end
    handles.mouse_boundary = plot(NaN,NaN,'-c');
    handles.tailtip = plot(NaN,NaN,'r*');
    handles.nose = plot(NaN,NaN,'gx');
    handles.tailbase = plot(NaN,NaN,'rx');
    handles.com = plot(NaN,NaN,'c+');

    if params.nt_make_track_video
        writerObj = VideoWriter('mousetracking1.avi');
        writerObj.FrameRate = framerate;
        open(writerObj);
    end
else
    handles = [];
end

%%

% The actual videoanalysis part
% Runs a for loop trough all frames that need to be analysed specified by
% frameRange. For every frame, the background is substracted. Then, the
% resulting image is tresholded to have the remainig shape which is assumed
% to be the mouse. From this, the position of the mouse is calculated.
% Around this position the mean pixelvalue change is calculated that is
% used later for freeze detection.


n_frames = ceil((time_range(2)-time_range(1)) * framerate);
frametimes = NaN(n_frames,1);

logmsg(['Detecting mouse starting from ' num2str(time_range(1)) ' s.']);
try
    vid.CurrentTime = time_range(1);
catch me
    logmsg([me.message ' in ' recordfilter(record)]);
    return
end

stim_position = struct('stim_id',[],'com',[]);
stim_position = stim_position([]);

position = struct('com',NaN(n_frames,2),'tailtip',NaN(n_frames,2),...
    'tailbase',NaN(n_frames,2),'nose',NaN(n_frames,2));
vidDif = NaN(n_frames,1); % for the difference per frame
Frame = [];
i = 1;

% DisableKeysForKbCheck(231); % ignore for laptop Alexander
prev_mousepos = [];
prev_stimpos = [];

start = tic();


mouse_area = [];
black_threshold = [];
mouse_length = [];
matched_criteria = [];


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
        gFrame = uint8(double(Frame).^params.nt_play_gamma / (255^params.nt_play_gamma) * 255);
        %handles.image = image(handles.video,gFrame); %#ok<NASGU>
        handles.image.CData = gFrame;
    end

    if isfield(measures,'markers')
        cur_stim_ids = nt_which_stimuli(measures.markers,frametimes(i),params);
    else
        cur_stim_ids = [];
    end
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

    [mousepos,stimpos,~,stat] = nt_get_mouse_position( Frame,bg,n_cur_stims,params,handles,mask,prev_mousepos,prev_stimpos,verbose);

    mouse_area(i) = stat.mouse_area;
    black_threshold(i) = stat.black_threshold;
    mouse_length(i) = stat.mouse_length;
    matched_criteria(i) = stat.matched_criteria;

    position.com(i,:) = mousepos.com;
    position.tailtip(i,:) = mousepos.tailtip;
    position.tailbase(i,:) = mousepos.tailbase;
    position.nose(i,:) = mousepos.nose;

    if all(~isnan(mousepos.com))
        prev_mousepos.com = mousepos.com;
    end
    if all(~isnan(mousepos.tailtip))
        prev_mousepos.tailtip = mousepos.tailtip;
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
        handles.clock.String = [num2str(vid.CurrentTime,'%0.2f') ' s'];
        drawnow
        if params.nt_make_track_video
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
save(filename,'frametimes','position','stim_position','params','record')
logmsg(['Saved tracking data in ' filename]);

if params.nt_make_track_video
    close(writerObj);
end

clear vidobj


stat = [];
stat.mouse_area = mouse_area;
stat.black_threshold = black_threshold;
stat.mouse_length = mouse_length;

if verbose
    mask = logical(matched_criteria);
    logmsg(['Mouse area, median = ' num2str(median(mouse_area(mask)))])
    logmsg(['Mouse area, min = ' num2str(min(mouse_area(mask)))])
    logmsg(['Mouse area, max = ' num2str(max(mouse_area(mask)))])
    logmsg(['Mouse length, median = ' num2str(median(mouse_length(mask)))])
    logmsg(['Mouse length, min = ' num2str(min(mouse_length(mask)))])
    logmsg(['Mouse length, max = ' num2str(max(mouse_length(mask)))])
    logmsg(['Black threshold, median = ' num2str(median(black_threshold(mask)))])
    logmsg(['Black threshold, min = ' num2str(min(black_threshold(mask)))])
    logmsg(['Black threshold, max = ' num2str(max(black_threshold(mask)))])
end



logmsg('You might want to run nt_detect_freezing')
logmsg('Finished mouse tracking.')
