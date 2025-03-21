function record = nt_track_behavior(record,h_dbfig,verbose)
%nt_track_behavior Tracks neurotar experiment from movie and neurotar
%
%  RECORD = nt_track_behavior( RECORD, [VERBOSE=true])
%
% 2023, Alexander Heimel, Zhiting Ren
%
% Times are aligned to clock of neurotar, with start of first trigger
% set to time = 0.
% align times from this common trigger and then multiply master time with specific
% multiplier to obtain time in [picamera] values. See also
% nt_default_parameters.

% Coordinates frames:
%    Arena coordinates: x,y position in circular arena in mm
%    Neurotar (mouse) coordinates: x,y position on neurotar frame in mm 
%    Overhead coordinates: x,y position in overhead camera image in pixels
% To move between coordinate frames:
%    [overhead_x, overhead_y] = change_neurotar_to_overhead_coordinates(neurotar_x,neurotar_y,measures,params)
%    [neurotar_x, neurotar_y] = change_overhead_to_neurotar_coordinates(overhead_x,overhead_y,measures,params);
%    [arena_x, arena_y] = change_neurotar_to_arena_coordinates(neurotar_x,neurotar_y)
%    [neurotar_x, neurotar_y] = change_arenar_to_neurotar_coordinates(arena_x,arena_y)


global measures global_record %#ok<GVMIS>
global_record = record;
evalin('base','global measures');
evalin('base','global global_record');
logmsg('Measures available in workspace as ''measures'', record as ''global_record''.');

warning('on')

if nargin<2 || isempty(h_dbfig)
    h_dbfig = [];
end

if nargin<3 || isempty(verbose)
    verbose = true;
end

%% Preamble
measures = record.measures;
params = nt_default_parameters(record);

if isempty(measures)
    measures = struct([]);
end
if ~isfield(measures,'markers')
    measures(1).markers = struct([]);
end
if ~isfield(measures,'trigger_times')
    measures.trigger_times = {};
end
if ~isfield(measures,'overhead_neurotar_headring') || isempty(measures.overhead_neurotar_headring)
    measures.overhead_neurotar_headring = params.overhead_neurotar_headring;
end
if ~isfield(measures,'overhead_neurotar_center') || isempty(measures.overhead_neurotar_center)
    measures.overhead_neurotar_center = params.overhead_neurotar_center;
end

set(groot, 'defaultAxesCreateFcn', @(ax,~) disableDefaultInteractivity(ax))

state.master_time = 0;

params = nt_default_parameters(record);

% update object_positions format
if ~isfield(measures,'object_positions')
    measures.object_positions = []; % n x 5: time,x,y,coordinate system,object_id
elseif size(measures.object_positions,2) ~= 5 % old format
    measures.object_positions = nt_update_object_position_format(measures.object_positions,params,record);
end

%% Load data
nt_data = nt_load_neurotar_data(record);
if isempty(nt_data)
    logmsg(['Could not load Neurotar data for ' recordfilter(record)]);
    nt_data = nt_load_mouse_tracks(record);
end





%% Open movies
[handles.vidobj,measures.trigger_times,active_cameras] = nt_open_videos(record,state.master_time);
num_cameras = length(params.nt_camera_names);

% get size of overhead camera
params.overhead_camera_width = handles.vidobj{params.nt_overhead_camera}.Width;
measures.overhead_camera_width = params.overhead_camera_width;
params.overhead_camera_height = handles.vidobj{params.nt_overhead_camera}.Height;
measures.overhead_camera_height = params.overhead_camera_height;

if isempty(nt_data)
    % no previous tracking data, using overhead camera movie as main time

    if isempty(active_cameras)
        errormsg('No neurotar data and no video data. I don''t know what to do. I quit.');
        return
    end

    nt_data.Time = NaN(handles.vidobj{params.nt_overhead_camera}.NumFrames,1);
    nt_data.Time = 0:1/handles.vidobj{params.nt_overhead_camera}.FrameRate:handles.vidobj{params.nt_overhead_camera}.Duration;
    nt_data.Speed = NaN(size(nt_data.Time));
    nt_data.X = NaN(size(nt_data.Time));
    nt_data.Y = NaN(size(nt_data.Time));
    nt_data.CoM_X = NaN(size(nt_data.Time));
    nt_data.CoM_Y = NaN(size(nt_data.Time));
    nt_data.tailbase_X = NaN(size(nt_data.Time));
    nt_data.tailbase_Y = NaN(size(nt_data.Time));
    nt_data.alpha = NaN(size(nt_data.Time));
    nt_data.Forward_speed = NaN(size(nt_data.Time));
    nt_data.Angular_velocity = NaN(size(nt_data.Time));
    nt_data.Object_distance = NaN(size(nt_data.Time));
end

%max_time = nt_data.Time(end);


%% Set up figure
handles = nt_draw_track_window(handles,record,get_list_of_actions(),nt_data,state,measures,params);
update_neurotar_frame(handles.overhead_neurotar_frame,params);
set(handles.fig_main,'WindowKeyPressFcn',@keypressfcn);
set(handles.fig_main,'UserData',struct('action',''));
set(handles.fig_main,'CloseRequestFcn',@closerequestfcn);

handles.h_dbfig = h_dbfig;


%% Main playback
logmsg('Starting play')
set(handles.text_state,'String','Playing');

state.playback_speed = 1;
state.loop = true;
state.play = true;
state.newframe = false;
state.close_window = false;
state.jumptime = 0;
state.video_framerate = handles.vidobj{1}.FrameRate; % should go to params
state.interframe_time = 1/state.video_framerate; % should go to params
state.frame_update = 1;
state.loop_time = 0.03; % s
state.fps = state.video_framerate;
state.extra_delay = 0.0; % to adjust fps to video_framerate

set(handles.text_playback_speed,'String',num2str(state.playback_speed))

figure(handles.fig_main);
real_time_start = tic;
real_time_prev = toc(real_time_start);
jumped = false;
while state.loop
    if state.play || state.newframe
        if state.jumptime ~= 0
            % adjust jump to fit in recording of all camera's
            for c = active_cameras
                if handles.vidobj{c}.CurrentTime + state.jumptime > handles.vidobj{c}.Duration
                    state.jumptime = handles.vidobj{c}.Duration - handles.vidobj{c}.CurrentTime;
                end
                if handles.vidobj{c}.CurrentTime + state.jumptime < 0
                    state.jumptime = -handles.vidobj{c}.CurrentTime;
                end
            end % c
            % make jump if jump still exists
            if state.jumptime~=0
                for c = active_cameras
                    handles.vidobj{c}.CurrentTime = handles.vidobj{c}.CurrentTime + state.jumptime;
                end % c
            end
            state.jumptime = 0;
            jumped = true;
        end

        % check if all cameras have frames
        for c = active_cameras
            if ~hasFrame(handles.vidobj{c})
                state.newframe = false;
                state.play = false;
                set(handles.text_state,'String','Paused')
            end
        end % c

        if state.play || state.newframe
            camera_times_in_master_time = zeros(1,num_cameras);
            for c = active_cameras
                handles.camera_image(c).CData = readFrame(handles.vidobj{c});
                camera_times_in_master_time(c) = (handles.vidobj{c}.CurrentTime - measures.trigger_times{c}(1)) / params.picamera_time_multiplier;
            end
            state.master_time = mean(camera_times_in_master_time(active_cameras));
            state.newframe = false;
        end

        state.ind_past = find( nt_data.Time > state.master_time - params.nt_mouse_trace_window,1);
        state.ind_current = state.ind_past + find( nt_data.Time(state.ind_past:end) > state.master_time,1 ) - 2 ;

        if isempty(state.ind_current) || state.ind_current == 0
            state.ind_current = 1;
            logmsg('No time before current time.')
        end
        state.ind_future = state.ind_current + find( nt_data.Time(state.ind_current:end) > state.master_time + params.nt_mouse_trace_window,1) - 2;

        state.X = nt_data.X(state.ind_current);
        state.Y = nt_data.Y(state.ind_current);
        state.alpha = nt_data.alpha(state.ind_current);
        state.CoM_X = nt_data.CoM_X(state.ind_current);
        state.CoM_Y = nt_data.CoM_Y(state.ind_current);
        state.tailbase_X = nt_data.tailbase_X(state.ind_current);
        state.tailbase_Y = nt_data.tailbase_Y(state.ind_current);



        handles = update_all_panels(nt_data,measures,state,handles,jumped,params);
        jumped = false;
    end % newframe

    % handle fast playback
    if state.playback_speed>1
        for f = 2:state.playback_speed
            for c = active_cameras
                if ~hasFrame(handles.vidobj{c})
                    state.newframe = false;
                    state.play = false;
                    set(handles.text_state,'String','Paused')
                else
                    readFrame(handles.vidobj{c});
                end
            end
        end
    end

    % Pause to maintain the natural frame rate
    real_time = toc(real_time_start);
    d = real_time - real_time_prev;
    if d < state.interframe_time/state.playback_speed
        pause(state.interframe_time/state.playback_speed - d + state.extra_delay);
        real_time = toc(real_time_start);
    end
    d = real_time - real_time_prev;
    real_time_prev = real_time;

    state.fps = 0.9*state.fps + 0.1*round(1/d); % averaging framerate

    if state.fps < state.video_framerate*state.playback_speed && state.extra_delay>-state.interframe_time
        state.extra_delay = state.extra_delay - 0.001;
    elseif state.fps > state.video_framerate*state.playback_speed && state.extra_delay<state.interframe_time
        state.extra_delay = state.extra_delay + 0.001;
    end

    % Perform action
    action = get(handles.fig_main,'Userdata').('action');
    [measures,state,handles,params] = take_action(action,measures,state,handles,record,params);

end % play loop

set(handles.text_state,'String','Stopped')
set(handles.fig_main,'WindowKeyPressFcn',[]);
set(handles.fig_main,'CloseRequestFcn','closereq');
if ishandle(handles.fig_main_help)
    close(handles.fig_main_help);
end
logmsg('Finished tracking and updating record.');
record.measures = measures;
if state.close_window
    close(handles.fig_main);
    delete(handles.fig_main);
end
clear handles.vidobj

global_record = record;

end


%% Update all panels
function handles = update_all_panels(nt_data,measures,state,handles,jumped,params)

set(handles.text_time,'String',num2str(state.master_time,'%0.2f'))
handles.timeline_current_time.XData = state.master_time * [1 1];

% update arena on overhead camera image
nt_update_arena_walls(handles.overhead_arena,state,params);

% handles.overhead_nose.XData = state.X;
% handles.overhead_nose.YData = state.Y;
% handles.overhead_com.XData = state.CoM_X;
% handles.overhead_com.YData = state.CoM_Y;
% handles.overhead_tailbase.XData = state.tailbase_X;
% handles.overhead_tailbase.YData = state.tailbase_Y;


handles.overhead_mouse.XData = [state.X state.CoM_X state.tailbase_X];
handles.overhead_mouse.YData = [state.Y state.CoM_Y state.tailbase_Y];



% update mouse in arena drawing
if params.nt_show_arena_panel
    handles.arena_trace.XData = nt_data.X(state.ind_past:state.ind_current);
    handles.arena_trace.YData = nt_data.Y(state.ind_past:state.ind_current);
    mouse_poly = 1.5* [0 10;-3 -2;3 -2;0 10]';
    alpha_rad = state.alpha/180*pi;
    rot = [cos(alpha_rad) -sin(alpha_rad); sin(alpha_rad) cos(alpha_rad) ];
    mouse_poly = rot * mouse_poly;
    handles.arena_mouse.XData = state.X + mouse_poly(1,:);
    handles.arena_mouse.YData = state.Y + mouse_poly(2,:);
end

handles = update_object_positions(measures,state,handles,params);

% update speed  velocity plots
ind = state.ind_past:state.ind_future;
handles.speed_trace.XData = nt_data.Time(ind);
handles.speed_trace.YData = nt_data.Forward_speed(ind);
handles.speed_xaxis.XData = [state.master_time-params.nt_mouse_trace_window state.master_time+params.nt_mouse_trace_window];
handles.speed_xaxis.YData = [0 0];
handles.speed_yaxis.XData = [state.master_time state.master_time];
handles.speed_yaxis.YData = [-250 250];
xl = [state.master_time-params.nt_mouse_trace_window state.master_time+params.nt_mouse_trace_window];
handles.panel_neurotar_speed.XAxis.Limits = xl; % much faster than xlim
if ~jumped
    nt_show_markers_fast(measures.markers,handles.panel_neurotar_speed,params,xl,[-250 250]);
else
    nt_show_markers(measures.markers,handles.panel_neurotar_speed,params,xl,[-250 250]);
end

% update angular velocity trace
if params.nt_show_rotation_trace
    handles.rotation_trace.XData = nt_data.Time(ind);
    handles.rotation_trace.YData = nt_data.Angular_velocity(ind);
    handles.rotation_xaxis.XData = [state.master_time-params.nt_mouse_trace_window state.master_time+params.nt_mouse_trace_window];
    handles.rotation_xaxis.YData = [0 0];
    handles.rotation_yaxis.XData = [state.master_time state.master_time];
    handles.rotation_yaxis.YData = [-360 360];
    xl = [state.master_time-params.nt_mouse_trace_window state.master_time+params.nt_mouse_trace_window];
    handles.panel_neurotar_rotation.XAxis.Limits = xl; % faster than xlim
    if ~jumped
        nt_show_markers_fast(measures.markers,handles.panel_neurotar_rotation,params,xl,[-360 360]);
    else
        nt_show_markers(measures.markers,handles.panel_neurotar_rotation,params,xl,[-360 360]);
    end
end

% update object distance trace
if params.nt_show_distance_trace
    handles.distance_trace.XData = nt_data.Time(ind);
    if isreal(nt_data.Object_distance(ind))
        handles.distance_trace.YData = nt_data.Object_distance(ind);
    else
        handles.distance_trace.YData = NaN(size(ind));
        warning('NT_TRACK_BEHAVIOR:COMPLEX_OBJECT_DISTANCE','Complex object distance')
        warning('off','NT_TRACK_BEHAVIOR:COMPLEX_OBJECT_DISTANCE')
    end
    handles.distance_xaxis.XData = [state.master_time-params.nt_mouse_trace_window state.master_time+params.nt_mouse_trace_window];
    handles.distance_xaxis.YData = [0 0];
    handles.distance_yaxis.XData = [state.master_time state.master_time];
    handles.distance_yaxis.YData = [0 300];
    xl = [state.master_time-params.nt_mouse_trace_window state.master_time+params.nt_mouse_trace_window];
    handles.panel_neurotar_distance.XAxis.Limits = xl; % faster than xlim
    if ~jumped
        nt_show_markers_fast(measures.markers,handles.panel_neurotar_distance,params,xl,[0 300]);
    else
        nt_show_markers(measures.markers,handles.panel_neurotar_distance,params,xl,[0 300]);
    end
end

set(handles.text_fps,'String',num2str(round(state.fps)));

if params.nt_drawnow_limitrate
    drawnow limitrate % only update at 20 fps
else
    drawnow
end

end




function handles = update_object_positions(measures,state,handles,params)
% updates the location of the objects
% if isempty(measures.object_positions)
%     ind = find(cellfun(@(x) ~isempty(x),handles.arena_object));
%     cellfun(@delete,handles.arena_object(ind));
%     handles.arena_object(ind) = {[]};
%
%     ind = find(cellfun(@(x) ~isempty(x),handles.overhead_object));
%     cellfun(@delete,handles.overhead_object(ind));
%     handles.overhead_object(ind) = {[]};
% end

if isempty(measures.object_positions)
    return
end

stim_ids = nt_which_stimuli(measures.markers,state.master_time,params);
for i=1:length(stim_ids)
    stim_id = stim_ids(i);
    [overhead_x,overhead_y,arena_x,arena_y] = nt_get_stim_position_from_measures(measures,stim_id,state,params);

    if params.nt_show_arena_panel
        if ~isnan(arena_x) && ~isnan(arena_y)
            if ishandle(handles.arena_object{stim_id})
                if handles.arena_object{stim_id}.XData ~= arena_x || handles.arena_object{stim_id}.YData ~= arena_y
                    handles.arena_object{stim_id}.XData = arena_x;
                    handles.arena_object{stim_id}.YData = arena_y;
                end
            else
                hold(handles.panel_arena,'on');
                handles.arena_object{stim_id} = plot(handles.panel_arena,arena_x,arena_y,'x','Color',[0 1 0],'MarkerSize',8);
            end
        end
    end

    % show object in overhead panel
    if ishandle(handles.overhead_object{stim_id})
        %    if handles.overhead_object{stim_id}.XData ~= overhead_x || handles.overhead_object{stim_id}.YData ~= overhead_y
        if handles.overhead_object{stim_id}.Position(end-1) ~= overhead_x || handles.overhead_object{stim_id}.Position(end) ~= overhead_y
            % handles.overhead_object{stim_id}.XData = overhead_x;
            % handles.overhead_object{stim_id}.YData = overhead_y;
            %  handles.overhead_object{stim_id}.Position = [handles.panel_video(2),overhead_x,overhead_y];
            handles.overhead_object{stim_id}.Position = [overhead_x,overhead_y,0];
        end
    else
        hold(handles.panel_video(2),'on');
        % handles.overhead_object{stim_ids(i)} = plot(handles.panel_video(2),overhead_x,overhead_y,'s','Color',[0 1 0]);
        handles.overhead_object{stim_id} = text(handle(handles.panel_video(2)),overhead_x,overhead_y,num2str(stim_id),'Color',[0 1 0]);
        handles.overhead_object{stim_id}.Position = [overhead_x,overhead_y,0];
    end
end % i

ind_not_present = 1:9;
ind_not_present(stim_ids) = []; % faster than setdiff
mask_handles = cellfun( @(x) ~isempty(x),handles.overhead_object(ind_not_present));
cellfun(@delete,handles.overhead_object(ind_not_present(mask_handles)));
handles.overhead_object(ind_not_present(mask_handles)) = {[]};

mask_handles = cellfun( @(x) ~isempty(x),handles.arena_object(ind_not_present));
cellfun(@delete,handles.arena_object(ind_not_present(mask_handles)));
handles.arena_object(ind_not_present(mask_handles)) = {[]};


end




%% Take action
function [measures,state,handles,params] = take_action(action,measures,state,handles,record,params)
if ~isempty(action) % && ~strcmp(action,prev_action)
    switch action % order list alphabetically
        case 'backward_frame'
            state.newframe = true;
            state.jumptime = -2 * state.interframe_time;
        case 'backward_short'
            state.newframe = true;
            state.jumptime = -0.5 - state.interframe_time;
        case 'backward_marker'
            ind = find([measures.markers.time]<state.master_time-0.04,1,'last');
            if ~isempty(ind)
                state.newframe = true;
                state.jumptime = measures.markers(ind).time - state.master_time;
            end
        case 'backward_medium'
            state.newframe = true;
            state.jumptime = -5 - state.interframe_time;
        case 'backward_long'
            state.newframe = true;
            state.jumptime = -60 - state.interframe_time;
        case 'forward_frame'
            state.newframe = true;
            state.jumptime = 0;
        case 'forward_short'
            state.newframe = true;
            state.jumptime = 0.5 - state.interframe_time;
        case 'forward_medium'
            state.newframe = true;
            state.jumptime = 5 - state.interframe_time;
        case 'forward_long'
            state.newframe = true;
            state.jumptime = 60 - state.interframe_time;
        case 'forward_marker'
            if ~isempty(measures.markers)
                ind = find([measures.markers.time]>state.master_time+0.04,1);
                if ~isempty(ind)
                    state.newframe = true;
                    state.jumptime = measures.markers(ind).time - state.master_time;
                end
            end
        case 'goto'
            userdata = get(handles.fig_main,'UserData');
            if isfield(userdata,'time') && ~isempty(userdata.time)
                goto_time = userdata.time;
                userdata.time = [];
                set(handles.fig_main,'UserData',userdata);
            else
                answer = inputdlg('Go to second: ','Go to');
                goto_time = str2double(answer{1});
            end
            if ~isempty(goto_time) && isnumeric(goto_time) && ~isnan(goto_time)
                state.newframe = true;
                state.jumptime = goto_time - state.master_time;
            end

        case 'import_laser_log'
            %% Load laser triggers
            events = nt_load_laser_triggers(record,[],params);
            for i = 1:length(events)
                switch events(i).code
                    case 'p' % prey
                        measures.markers = nt_insert_marker(measures.markers,events(i).time,'v',params);
                        measures.markers = nt_insert_marker(measures.markers,events(i).time + events(i).duration,'t',params);
                    case 'b' % both
                        measures.markers = nt_insert_marker(measures.markers,events(i).time,'v',params);
                        measures.markers = nt_insert_marker(measures.markers,events(i).time + events(i).duration,'t',params);
                        measures.markers = nt_insert_marker(measures.markers,events(i).time,'1',params);
                        measures.markers = nt_insert_marker(measures.markers,events(i).time + events(i).duration,'0',params);
                    case 'o' % opto
                        measures.markers = nt_insert_marker(measures.markers,events(i).time,'1',params);
                        measures.markers = nt_insert_marker(measures.markers,events(i).time + events(i).duration,'0',params);
                end
            end
            nt_show_markers(measures.markers,handles.panel_timeline,params);
            nt_show_position_changes(measures.object_positions,handles.panel_timeline,params);

            state.newframe = true;
            state.jumptime = -state.interframe_time;

            record.measures = measures;
            update_record(record,handles.h_dbfig,true);

            logmsg('Imported laser log')
        case 'marker_add'
            set(handles.fig_main,'WindowKeyPressFcn',[]);
            pause(0.01)
            prev_state = get(handles.text_state,'String');
            set(handles.text_state,'String','Choose marker');
            fprintf('Choose which marker to add by pressing key: ')
            drawnow
            waitforbuttonpress;
            key = get(gcf,'CurrentCharacter');
            fprintf([key '\n']);
            [measures.markers,stim_id] = nt_insert_marker(measures.markers,state.master_time,key,params,true,handles);
            if strcmp(key,params.nt_stop_marker)
                measures.object_positions(end+1,:) = [state.master_time NaN NaN params.ARENA stim_id];
                [~,ind] = sort(measures.object_positions(:,1));
                measures.object_positions = measures.object_positions(ind,:);
            end
            nt_show_markers(measures.markers,handles.panel_timeline,params);
            set(handles.text_state,'String',prev_state);
            state.newframe = true;
            state.jumptime = -state.interframe_time;

            record.measures = measures;

            update_record(record,handles.h_dbfig,true);

            set(handles.fig_main,'WindowKeyPressFcn',@keypressfcn);
        case 'marker_delete'
            answer = questdlg('Do you want to delete next marker?','Delete marker','Yes','No','No');
            switch answer
                case 'Yes'
                    [measures.markers,removed_marker] = delete_next_marker(measures.markers,state.master_time);
                    if strcmp(removed_marker.marker,params.nt_stop_marker)
                        % remove object_position entries too
                        ind = find(measures.object_positions(:,1)==removed_marker.time);
                        if ~isempty(ind)
                            measures.object_positions(ind,:) = [];
                        end
                    end
                    nt_show_markers(measures.markers,handles.panel_timeline,params);
                    state.newframe = true;
                    state.jumptime = -state.interframe_time;
            end

            record.measures = measures;
            update_record(record,handles.h_dbfig,true);

        case 'marker_delete_all'
            answer = questdlg('Do you want to delete all markers?','Delete all markers','Yes','No','No');
            switch answer
                case 'Yes'
                    measures.markers = [];
                    nt_show_markers(measures.markers,handles.panel_timeline,params);
                    state.newframe = true;
                    state.jumptime = -state.interframe_time;
            end

            record.measures = measures;
            update_record(record,handles.h_dbfig,true);

        case 'position_delete'
            ind = find(measures.object_positions(:,1)<=state.master_time,1,'last');
            if ~isempty(ind)
                logmsg(['Deleting object position: ' mat2str(measures.object_positions(ind,:))])
                measures.object_positions(ind,:) = [];
            else
                logmsg('No previous object position to delete');
            end
            state.newframe = true;
            state.jumptime = -state.interframe_time;

            record.measures = measures;
            nt_show_position_changes(measures.object_positions,handles.panel_timeline,params);

            update_record(record,handles.h_dbfig,true);

        case 'quit'
            logmsg('Quit tracking. Exiting main loop and closing window.');
            state.loop = false;
            state.close_window = true;
        case 'show_help'
            if ishandle(handles.fig_main_help)
                figure(handles.fig_main_help);
            else
                handles.fig_main_help = show_help(params);
            end
        case 'stop'
            logmsg('Stopped tracking. Exiting main loop.');
            state.loop = false;
            state.close_window = false;
        case 'set_trigger'
            set(handles.fig_main,'WindowKeyPressFcn',[]);
            camera = ask_for_camera('Set trigger');
            measures.trigger_times{camera}(1) = handles.vidobj{camera}.CurrentTime;
            handles.vidobj{camera}.CurrentTime = measures.trigger_times{camera}(1) + state.master_time * params.picamera_time_multiplier ;
            state.jumptime = -state.master_time;
            state.newframe = true;
            %jumptime = -1 * interframe_time;

            record.measures = measures;
            update_record(record,handles.h_dbfig,true);

            set(handles.fig_main,'WindowKeyPressFcn',@keypressfcn);
        case 'set_led_position'
            set(handles.fig_main,'WindowKeyPressFcn',[]);
            camera = ask_for_camera('Set LED');
            [x,y] = get_location_on_camera(handles,camera);
            measures.led_position{camera} = round([x,y]);
            putative_trigger_time = find_led_on(handles.vidobj{camera},x,y);
            if ~isempty(putative_trigger_time)
                logmsg(['Putative trigger time from start of movie: ' num2str(putative_trigger_time) ' s.']);
                logmsg(['Putative trigger time on current timeline: ' num2str(putative_trigger_time-measures.trigger_times{camera}(1)) ' s.']);
            end
            record.measures = measures;
            update_record(record,handles.h_dbfig,true);

        case {'set_real_object_position','set_virtual_object_position'}
            stim_ids = nt_which_stimuli(measures.markers,state.master_time,params);
            if isempty(stim_ids)
                if strcmp(action,'set_real_object_position')
                    marker = 'o';
                else
                    marker = 'v';
                end
                logmsg(['No stimulus currently present. Adding marker ''' marker '''']);
                [measures.markers,stim_id] = nt_insert_marker(measures.markers,state.master_time,marker,params);
            elseif length(stim_ids)>1
                stim_id = -1;
                while ~ismember(stim_id,stim_ids)
                    fprintf(['Choose which stim_id ' mat2str(stim_ids) ' by pressing number key: '])
                    drawnow
                    waitforbuttonpress;
                    key = get(gcf,'CurrentCharacter');
                    fprintf([key '\n']);
                    stim_id = str2double(key);
                    if ~ismember(stim_id,stim_ids)
                        disp(['Stim_id ' key ' is not currently present.']);
                    end
                end
            else
                stim_id = stim_ids;
            end
            [overhead_x,overhead_y] = get_location_on_camera(handles,params.nt_overhead_camera);
            if params.neurotar && strcmp(action,'set_real_object_position')
                [neurotar_x,neurotar_y] = nt_change_overhead_to_neurotar_coordinates(overhead_x,overhead_y,params);
                [arena_x,arena_y] = nt_change_neurotar_to_arena_coordinates(neurotar_x,neurotar_y,...
                    state.X,state.Y,state.alpha,params);
                measures.object_positions(end+1,:) = [state.master_time arena_x arena_y params.ARENA stim_id];
            else
                measures.object_positions(end+1,:) = [state.master_time overhead_x overhead_y params.OVERHEAD stim_id];

            end
            [~,ind] = sort(measures.object_positions(:,1));
            measures.object_positions = measures.object_positions(ind,:);
            nt_show_markers(measures.markers,handles.panel_timeline,params);
            nt_show_position_changes(measures.object_positions,handles.panel_timeline,params);
            %update_object_positions(measures,state,handles,params);

            record.measures = measures;
            update_record(record,handles.h_dbfig,true);

            drawnow
            state.newframe = true;
            state.jumptime = -state.interframe_time;
        case 'set_neurotar_center'
            camera = params.nt_overhead_camera;
            [x,y] = get_location_on_camera(handles,camera);
            measures.overhead_neurotar_center = [x; y];
            params.overhead_neurotar_center = measures.overhead_neurotar_center;
            update_neurotar_center(handles.overhead_neurotar_center,params);
            update_neurotar_frame(handles.overhead_neurotar_frame,params);

            record.measures = measures;
            update_record(record,handles.h_dbfig,true);

            state.newframe = true;
            state.jumptime = -state.interframe_time;
        case 'set_neurotar_headring'
            camera = params.nt_overhead_camera;
            [x,y] = get_location_on_camera(handles,camera);
            measures.overhead_neurotar_headring = [x; y];
            params.overhead_neurotar_headring = measures.overhead_neurotar_headring;
            update_neurotar_headring(handles.overhead_neurotar_headring,params);
            update_neurotar_frame(handles.overhead_neurotar_frame,params);
            update_record(record,handles.h_dbfig,true);

            state.newframe = true;
            state.jumptime = -state.interframe_time;
        case 'speed_original'
            state.playback_speed = 1;
            set(handles.text_playback_speed,'String',num2str(state.playback_speed))
        case 'speed_increase'
            state.playback_speed = increase_speed(state.playback_speed);
            set(handles.text_playback_speed,'String',num2str(state.playback_speed))
        case 'speed_decrease'
            state.playback_speed = decrease_speed(state.playback_speed);
            set(handles.text_playback_speed,'String',num2str(state.playback_speed))
        case 'toggle_behavior_markers'
            params.nt_show_behavior_markers = ~params.nt_show_behavior_markers;
            nt_show_markers(measures.markers,handles.panel_timeline,params);
        case 'toggle_drawnow_limitrate'
            params.nt_drawnow_limitrate = ~params.nt_drawnow_limitrate;
        case 'toggle_play'
            state.play = not(state.play);
            if state.play
                set(handles.text_state,'String','Playing')
            else
                set(handles.text_state,'String','Paused')
            end
            set_button_icon(handles.toggle_play_button,state.play);
        case 'update_camera_distortion'
            input = str2num(get(handles.edit_camera_distortion,'String')); %#ok<ST2NM>
            if ~isnan(input)
                params.overhead_camera_distortion = input;
                measures.overhead_camera_distortion = input;
            end
            input = str2num(get(handles.edit_camera_neurotar_center,'String')); %#ok<ST2NM>
            if ~isnan(input)
                params.overhead_neurotar_center = input;
                measures.overhead_neurotar_center = input;
            end
            input = str2num(get(handles.edit_camera_angle,'String')); %#ok<ST2NM>
            if ~isnan(input)
                params.overhead_camera_angle = input/180*pi;
                measures.overhead_camera_angle = input/180*pi;
            end
            input = str2num(get(handles.edit_time_multiplier,'String')); %#ok<ST2NM>
            if ~isnan(input)
                params.picamera_time_multiplier = input;
                measures.picamera_time_multiplier = input;
            end

            set(handles.edit_camera_distortion,'String',mat2str(params.overhead_camera_distortion));
            set(handles.edit_camera_neurotar_center,'String',mat2str(params.overhead_neurotar_center));
            set(handles.edit_camera_angle,'String',mat2str(params.overhead_camera_angle/pi*180));
            set(handles.edit_time_multiplier,'String',mat2str(params.picamera_time_multiplier));

            update_neurotar_frame(handles.overhead_neurotar_frame,params);
            if params.neurotar
                update_neurotar_center(handles.overhead_neurotar_center,params);
            end

            record.measures = measures;
            update_record(record,handles.h_dbfig,true);

            state.newframe = true;
    end
    userdata = get(handles.fig_main,'UserData');
    userdata.action = '';
    set(handles.fig_main,'UserData',userdata);
end % action different from prev_action
end


%% Action functions


function playback_speed = increase_speed(playback_speed)
switch playback_speed
    case 0.25
        playback_speed = 0.5;
    case 0.5
        playback_speed = 0.75;
    case 0.75
        playback_speed = 1;
    case 1
        playback_speed = 1.5;
    case 1.5
        playback_speed = 2;
    case 2
        playback_speed = 4;
    case 4
        playback_speed = 8;
    case 8
        playback_speed = 16;
end
end

function playback_speed = decrease_speed(playback_speed)
switch playback_speed
    case 0.5
        playback_speed = 0.25;
    case 0.75
        playback_speed = 0.5;
    case 1
        playback_speed = 0.75;
    case 1.5
        playback_speed = 1;
    case 2
        playback_speed = 1.5;
    case 4
        playback_speed = 2;
    case 8
        playback_speed = 4;
    case 16
        playback_speed = 8;
end
end

function help_fig = show_help(params)
actions = get_list_of_actions();
help_fig = uifigure('Name','Help','NumberTitle','off');
pos = get(help_fig,'position');
actions = actions(arrayfun(@(x) ~isempty(x.keys),actions)); % select actions with keys
margin = 10;
left = margin;
bottom = margin;
width = (pos(3)-3*margin)/2;
height = pos(4)-2*margin;
uitextarea(help_fig,'Value',arrayfun(@(x) [x.key_description ' - ' x.tooltip],actions,'UniformOutput',false),'Position',[left bottom width height]);

uitextarea(help_fig,'Value',arrayfun(@(x) [x.marker ' - ' x.description],params.markers,'UniformOutput',false),'Position',[left+width+margin bottom width height]);


end




function trigger_time = find_led_on(vidobj,x,y)
x = round(x);
y = round(y);
current_time = vidobj.CurrentTime;
vidobj.CurrentTime = 0;
number_of_frames = ceil(vidobj.Duration * vidobj.FrameRate );
redness = zeros(1,number_of_frames);
t = redness;
count = 0;
h = waitbar(0,'Analysing LED in movie');
while hasFrame(vidobj)
    count = count + 1;
    t(count) = vidobj.CurrentTime;
    frame = readFrame(vidobj);
    redness(count) = double(frame(y,x,1))/double(sum(frame(y,x,:))+0.001);
    if mod(count,2*60*30)==0
        disp([num2str(count/60/30) ' min']);
        mean_redness = mean(redness(1:count));
        std_redness = std(redness(1:count));
        ind = find(redness>mean_redness + 5*std_redness,1);
        if ~isempty(ind)
            disp('Found LED on.')
            break
        end
        waitbar(count/number_of_frames,h)
    end
end
close(h);
mean_redness = mean(redness(1:count));
std_redness = std(redness(1:count));
ind = find(redness>mean_redness + 5*std_redness,1);

figure
plot(t(1:count),redness(1:count))
hold on
plot(t([1 count]),mean_redness*[1 1],'r-');
plot(t([1 count]),(mean_redness+5*std_redness)*[1 1],'r--');
if ~isempty(ind)
    plot(t(ind),redness(ind),'or')
    trigger_time = t(ind);
else
    logmsg('Did not detect LED onset.')
    trigger_time = [];
end
vidobj.CurrentTime = current_time;
end


function camera = ask_for_camera(caption)
answer = inputdlg('Choose which camera [1,2,3]',...
    caption,1,{'1'});
switch answer{1}
    case '1'
        camera = 1;
    case '2'
        camera = 2;
    case '3'
        camera = 3;
    otherwise
        logmsg('Unknown camera. Selecting 1')
        camera = 1;
end
end

function [x,y] = get_location_on_camera(handles,~)
fig = handles.fig_main;
set(fig,'WindowKeyPressFcn',[]);
drawnow
[x,y] = ginput(1);
set(fig,'WindowKeyPressFcn',@keypressfcn);
end

function [x,y] = get_old_location_on_camera(handles,camera)
fig = handles.fig_main;
camera_image = handles.camera_image(camera);
set(fig,'WindowKeyPressFcn',[]);
pause(0.01)
set(fig,'WindowKeyPressFcn',@keypressfcn_zoomwindow)
old_userdata = get(fig,'UserData');
userdata = struct('gamma',1,'camera_image',camera_image,'xy',[]);
set(fig,'UserData',userdata);
disp('Press s to select position. Use +, - to change gamma.')
while isempty(userdata.xy)
    pause(0.001);
    userdata = get(fig,'UserData');
end
set(fig,'WindowKeyPressFcn',[])
x = userdata.xy(1);
y = userdata.xy(2);
set(fig,'UserData',old_userdata);
set(fig,'WindowKeyPressFcn',@keypressfcn);
end

function [markers,removed_marker] = delete_next_marker(markers,t)
mt = [markers.time];
ind = find(mt>t,1);
if isempty(ind)
    return
end
removed_marker = markers(ind);
markers(ind) = [];
end




%% Key capturing

function actions = get_list_of_actions()
% Double keys need to be listed above the single keys to be caught first.
actions = {...
    {'backward_frame',             {'leftarrow'},'Left arrow','Frame backward',90},...
    {'backward_marker',            {'p'},'p','Previous marker',80},...
    {'backward_medium',            {'leftarrow','alt'},'Alt + Left arrow','5 s backward',0},...
    {'backward_long',              {'leftarrow','control'},'Ctrl + Left arrow','1 min backward',0},...
    {'backward_short',             {'leftarrow','shift'},'Shift + Left arrow','0.5 s backward',0},...
    {'forward_frame',              {'rightarrow'},'Right arrow','Frame forward',110},...
    {'forward_marker',             {'n'},'n','Next marker',120},...
    {'forward_medium',             {'rightarrow','alt'},'Alt + Right arrow','5 s forward',0},...
    {'forward_long',               {'rightarrow','control'},'Ctrl + Right arrow','1 min forward',0},...
    {'forward_short',              {'rightarrow','shift'},'Shift + Right arrow','0.5 s forward',0},...
    {'goto',                       {'g'},'g','Go to time',0},...
    {'import_laser_log',           {'i','shift'},'I','Import laser log',0},...
    {'marker_add',                 {'m'},'m','Add marker',0},...
    {'marker_delete',              {'delete'},'Del','Delete next marker',0},...
    {'marker_delete_all',          {'d','shift'},'D','Delete all markers',0},...
    {'position_delete',            {'d'},'d','Delete previous object position',0},...
    {'show_help',                  {'h'},'h','Show help',1000},...
    {'set_led_position',           {'l','shift'},'L','Set LED position',0},...
    {'set_neurotar_center',        {'c','shift'},'C','Set Neurotar center',0},...
    {'set_neurotar_headring',      {'h','shift'},'H','Set Neurotar headring',0},...
    {'set_real_object_position',   {'o'},'o','Set real object position',0},...
    {'set_virtual_object_position',{'v'},'v','Set virtual object position',0},...
    {'set_trigger',                {'t','shift'},'T','Set first trigger',0},...
    {'speed_original',             {'equal'},'=','Original playback speed',0},...
    {'speed_increase',             {'equal','shift'},'+','Increase playback speed',0},...
    {'speed_decrease',             {'hyphen'},'-','Decrease playback speed',0},...
    {'stop',                       {'escape'},'Esc','Stop',0},...
    {'quit',                       {'q'},'q','Quit',0},...
    {'toggle_behavior_markers',    {'b'},'b','Toggle showing behavior markers',0},...
    {'toggle_drawnow_limitrate',   {'f'},'f','Toggle fast video updating',0},...
    {'toggle_play',                {'space'},'Space','Toggle play',100},...
    };

actions = cellfun( @(x) cell2struct(x,{'action','keys','key_description','tooltip','toolbutton_position'},2),actions);
end

function keypressfcn_zoomwindow(src,event)
%ax = get(src,'children');
%c = get(ax,'children');
userdata = get(src,'UserData');
switch event.Character
    case '+'
        if userdata.gamma > 0.1
            userdata.gamma = userdata.gamma - 0.1;
        end
        im = double(userdata.camera_image.CData);
        userdata.camera_image.CData = uint8((im/255).^userdata.gamma*255);
    case '-'
        if userdata.gamma < 4
            userdata.gamma = userdata.gamma + 0.1;
        end
        im = double(userdata.camera_image.CData);
        userdata.camera_image.CData = uint8((im/255).^userdata.gamma*255);
    case 's'
        [x,y] = ginput(1);
        userdata.xy = [x y];
end
set(src,'UserData',userdata);
end

function closerequestfcn(src,~)
disp('User closed tracking window')
userdata = get(src,'UserData');
userdata.action = 'quit';
set(src,'UserData',userdata);

end

function keypressfcn(src,event)
actions = get_list_of_actions();
found_key = false;
for i = 1:length(actions)
    if strcmp(event.Key,actions(i).keys{1})
        if isempty(event.Modifier) && isscalar(actions(i).keys)
            found_key = true;
            break;
        end
        if sort(event.Modifier)==sort(actions(i).keys(2:end))
            found_key = true;
            break;
        end
    end
end
userdata = get(src,'UserData');
if found_key
    if isempty(userdata.action)
        userdata.action = actions(i).action;
    end
    % disp(['Key: ' userdata.action] )
elseif ~strcmp(event.Key,'shift') && ~strcmp(event.Key,'alt') && ~strcmp(event.Key,'control')
    % disp(['Unparsed key ' event.Key '.']);
    userdata.action = '';
end
set(src,'UserData',userdata);
end

%% Other callback functions


function update_neurotar_headring(overhead_neurotar_headring,params)
overhead_neurotar_headring.XData = params.overhead_neurotar_headring(1);
overhead_neurotar_headring.YData = params.overhead_neurotar_headring(2);
end

function update_neurotar_center(overhead_neurotar_center,params)
overhead_neurotar_center.XData = params.overhead_neurotar_center(1);
overhead_neurotar_center.YData = params.overhead_neurotar_center(2);
end

function update_neurotar_frame(overhead_neurotar_frame,params)

if ~params.neurotar
    return
end


n_points = 50;
d = params.neurotar_halfwidth_mm;
neurotar_x = NaN;
neurotar_y = NaN;

if params.nt_show_boundaries
    neurotar_x = [  ...
        linspace(-d,-d,n_points) ...
        linspace(-d,d,n_points) ...
        linspace(d,d,n_points) ...
        linspace(d,-d,n_points) ];
    neurotar_y = [  ...
        linspace(-d,d,n_points) ...
        linspace(d,d,n_points) ...
        linspace(d,-d,n_points) ...
        linspace(-d,-d,n_points)  ];
end
if params.nt_show_bridge
    neurotar_x = [ neurotar_x NaN ...
        linspace(-d,d,n_points) ];
    neurotar_y = [ neurotar_y NaN ...
        linspace(0,0,n_points) ];
end
if params.nt_show_horizon
    d = 10000;
    neurotar_x = [neurotar_x NaN ...
        linspace(-d,-d,n_points) ...
        linspace(-d,d,n_points) ...
        linspace(d,d,n_points) ...
        linspace(d,-d,n_points) ];
    neurotar_y = [neurotar_y NaN...
        linspace(-d,d,n_points) ...
        linspace(d,d,n_points) ...
        linspace(d,-d,n_points) ...
        linspace(-d,-d,n_points)  ];
end


[overhead_x,overhead_y] = nt_change_neurotar_to_overhead_coordinates(neurotar_x,neurotar_y,params);
overhead_neurotar_frame.XData = overhead_x;
overhead_neurotar_frame.YData = overhead_y;

end


