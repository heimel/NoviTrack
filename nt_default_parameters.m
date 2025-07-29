function params = nt_default_parameters(record)
%nt_default_paramters Contains default parameters for neurotar analysis
%
%  PARAM = nt_default_parameters([RECORD])
%
%  Edit processparams_local for local and temporary edits to these default
%  parameters.
%
% 2023-2025, Alexander Heimel 

if nargin<1 
    record = [];
    record.setup = 'neurotar';
    record.stimulus = 'none';
end

% General
params = struct;

% Constants
params.ARENA = 1;
params.NEUROTAR = 2;
params.CAMERA = 3;
params.OVERHEAD = 4; 

% Data storage
% Below is a placeholder line. Replace to right folder in processparams_local.m
params.networkpathbase = '\\vs03.herseninstituut.knaw.nl\VS03-CSF-1\Temp'; 

% Communication between Pi's 
params.root_communication_path = '\\VS03\VS03-CSF-1\Communication';

% Debugging and testing 
params.nt_debug = false;

% User interface
params.fontsize = 8; % pt

% Automated mouse tracking
params.nt_play_gamma = 1; % default gamma to use for showing mouse movies
params.make_track_video = false; % to store a video with the tracked mouse

% Mouse detection 
params.nt_min_mouse_length = 120;
params.nt_max_mouse_area = 5000; % pxl, Max area that could be mouse
params.nt_min_component_area = 200; % pxl, Minimal area for component to be relevant
params.nt_min_mouse_area = 4000; % pxl, Minimal area a mouse could be
params.nt_min_stim_size = 0; % pxl, Minimal area for region that might be stimulus
params.nt_max_tail_width = 20; % pxl, Max tail width (to find tailbase)
params.nt_min_tail_distance = 70; % pxl, Minimal distance of tailbase to mouse C.o.M.
params.nt_dilation = ones(5); % for image dilation
params.nt_bg_normalization = 20;
params.nt_black_threshold = 0.25;
params.nt_min_black_threshold = 0.1;
params.nt_recompute_background = false; % force to recompute background


% Automated freezing detection parameters
params.wc_difScope = 50; % The range around mouse that is included in pixelchange analysis 
params.wc_difThreshold = 0.3; % threshold + minimum movement for difference between frames
% to be considered as no difference, fraction of average movement 
params.wc_deriv2thres = 0.08; % Threshold for 2nd derivative of vidDif for detecting freezing
params.wc_freezeduration_threshold = 0.5; %s minimum duration to call lack of movement a freeze
params.wc_freeze_smoother = [5,5]; % Number of frames that freeze analysis is averaging over before and after current frame


% For faster graphics
params.nt_graphicssmoothing = 'off';
params.nt_renderer = 'opengl'; % Matlab default is 'opengl'. On some computers 'painters' could be quicker
params.nt_drawnow_limitrate = false;

if strcmpi(record.setup,'neurotar')
    params.neurotar = true; % indicates if neurotar is present
else 
    params.neurotar = false;
end

% Camera's configuration

% placeholder values that may be overwritten by actual values
params.overhead_camera_width = 752;
params.overhead_camera_height = 550;
switch lower(record.setup)
    case 'neurotar'
        params.nt_camera_names = {'pilefteye','pioverhead','pirighteye'};
        params.nt_overhead_camera = 2;
        params.overhead_camera_distortion_method = 'fisheye_orthographic';
        params.overhead_camera_distortion = [339 339];
        params.overhead_camera_image_offset = [-4 4];
        params.overhead_camera_rotated = true;
        params.overhead_camera_angle = -0.13;
        params.neurotar_snout_distance_mm = 32;
        params.overhead_neurotar_headring = [275; 322]; % position of center of headring in overhead image
    case 'behavior_arena'
        params.nt_camera_names = {'side1','overhead','side2'};
        params.nt_overhead_camera = 2;
        params.overhead_camera_distortion_method = 'normal';
        params.overhead_camera_distortion = [1.4 NaN];
        params.overhead_camera_image_offset = [-4 4];
        params.overhead_camera_rotated = true;
        params.overhead_camera_angle = -0.0436;
        params.overhead_arena_center = [299 280];
    case 'circular_arena'
        params.nt_camera_names = {'side1','overhead','side2'};
        params.nt_overhead_camera = 2;
        params.overhead_camera_distortion_method = 'fisheye_orthographic';
        params.overhead_camera_distortion = [339 339];
        params.overhead_camera_image_offset = [-4 4];
        params.overhead_camera_rotated = true;
        params.overhead_camera_angle = -0.13;
    case 'elevated_plus_maze'
        params.nt_camera_names = {'overhead'};
        params.nt_overhead_camera = 1;
        params.overhead_camera_distortion_method = 'normal';
        params.overhead_camera_distortion = [1.4 NaN];
        params.overhead_camera_image_offset = [-4 4];
        params.overhead_camera_rotated = true;
        params.overhead_camera_angle = -0.0436;
        params.overhead_arena_center = [299 280];
    otherwise
        params.nt_camera_names = {'pilefteye','pioverhead','pirighteye'};
        params.nt_overhead_camera = 2;
end

if strcmpi(record.setup,'neurotar')
    if nargin<1 || isempty(record.date) ||datetime(record.date,'inputformat','yyyy-MM-dd') >  datetime('2023-11-03','inputformat','yyyy-MM-dd')
        % since about 2023-11-03
        params.overhead_camera_rotated = true;
        params.overhead_neurotar_center = [256; 238];  % position of center of bar in overhead image
        params.neurotar_snout_distance_mm = 32; % distance from snout to center of neurotar
    end

    if nargin<1 || isempty(record.date) || datetime(record.date,'inputformat','yyyy-MM-dd') <  datetime('2023-06-21','inputformat','yyyy-MM-dd')
        % before 2023-06-21
        params.overhead_camera_rotated = true;
        params.overhead_neurotar_center = [256; 238];  % position of center of bar in overhead image
        params.neurotar_snout_distance_mm = 0; % distance from snout to center of neurotar
    end
end

% Time synchronization
% Time of neurotar acquisition is taken as the master time
%
% align times at trigger and then multiply master time with specific
% multiplier to obtain time in [picamera] values
%
% video_time(camera) = measures.trigger_times{camera}(1)) + params.picamera_time_multiplier * master_time
params.picamera_time_multiplier = 1.0002;  
%
% laser_time = laser_trigger_time + params.laser_time_multiplier * master_time
params.laser_time_multiplier = 1.0002;  

% override with values from record.measures
if ~isempty(record) && isfield(record,'measures') && ~isempty(record.measures) 
    if isfield(record.measures,'overhead_neurotar_headring')
        params.overhead_neurotar_headring = record.measures.overhead_neurotar_headring;
    end
    if isfield(record.measures,'overhead_neurotar_center')
        params.overhead_neurotar_center = record.measures.overhead_neurotar_center;
    end
    if isfield(record.measures,'overhead_arena_center')
        params.overhead_arena_center = record.measures.overhead_arena_center;
    end
    if isfield(record.measures,'overhead_camera_distortion')
        params.overhead_camera_distortion = record.measures.overhead_camera_distortion;
    end
    if isfield(record.measures,'overhead_camera_shear')
        params.overhead_camera_shear = record.measures.overhead_camera_shear;
    end
    if isfield(record.measures,'overhead_camera_height')
        params.overhead_camera_height = record.measures.overhead_camera_height;
    end
    if isfield(record.measures,'overhead_camera_width')
        params.overhead_camera_width = record.measures.overhead_camera_width;
    end
    if isfield(record.measures,'overhead_camera_angle')
        params.overhead_camera_angle = record.measures.overhead_camera_angle;
    end
    if isfield(record.measures,'picamera_time_multiplier')
        params.picamera_time_multiplier = record.measures.picamera_time_multiplier;
    end
end

%% Arena
switch lower(record.setup)
    case 'neurotar'
        params.arena_shape = 'circular';
        params.arena_radius_mm = 162.5; %
        params.neurotar_halfwidth_mm = 260;
        % params.neurotar_snout_distance_mm = 45; % distance from snout to center of neurotar
    case 'behavior_arena'
        params.arena_shape = 'square';
        params.arena_diameter_mm = 320;
        params.arena_radius_mm = params.arena_diameter_mm / 2;
    case 'circular_arena'
        params.arena_shape = 'circular';
        params.arena_radius_mm = 162.5; % NOT CHECKED YET
    case 'elevated_plus_maze'
        params.arena_shape = 'plus';
        params.arena_open_arm_length_mm = 297;
        params.arena_open_arm_width_mm = 50;
        params.arena_closed_arm_length_mm = 300;
        params.arena_closed_arm_width_mm = 63;

        params.arena_radius_mm = params.arena_open_arm_length_mm + params.arena_closed_arm_width_mm/2;
        params.arena_diameter_mm = 2 * params.arena_radius_mm; 
end


%% Behaviors
% markers: 'marker','description','color','behavior','linked' (linked to
% stimulus or object)
%
% Note: behavior markers should be mutually exclusive, if you want two
% behaviors simultaneously, create a new behavior

marker_set = '';
switch lower(record.stimulus)
    % preferred way is to link the marker_set to the stimulus
    case 'firstandnovelobject'
        marker_set = 'object_investigation';
end
if isempty(marker_set)
    switch lower(record.condition)
        case 'looming_stimulus'
            marker_set = 'looming'; 
    end
end
if isempty(marker_set)
    switch lower(record.setup)
        case 'elevated_plus_maze'
            marker_set = 'elevated_plus_maze';
    end
end

if isempty(marker_set)
    if params.neurotar
        marker_set = 'prey_capture';
    else
        marker_set = 'object_investigation';
    end
end

markers = {};
% marker fields are 'marker','description','color','behavior','linked'
switch marker_set
    case 'prey_capture'
        markers{end+1} = {'t','stop stimulus',                  [1 0 0],    false,true};
        markers{end+1} = {'o','start physical stimulus',        [0 0 1],    false,true}; % e.g. object
        markers{end+1} = {'v','start virtual stimulus',         [0 1 0],    false,true}; % e.g. laser
        markers{end+1} = {'i','start IR virtual stimulus',      [1 0.5 0],  false,true}; % e.g. control laser
        markers{end+1} = {'h','start hanging physical stimulus',[0.4 0.2 1],false,true}; % e.g. finger or hanging object
        markers{end+1} = {'e','end session',                    [0 0 0],    false,false}; % e.g. mouse removed
        markers{end+1} = {'1','optolaser on',                   [0 0 1],    false,false}; % 
        markers{end+1} = {'0','optolaser off',                  [0 0 0],    false,false}; % 
        markers{end+1} = {'a','begin approach object',          [0 0.7 0],  true ,true};
        markers{end+1} = {'r','begin retreat from object',      [0.7 0 0],  true ,true};
    case 'object_investigation'
        markers{end+1} = {'t','Takeout object',[1 0 0]         ,false,true};
        markers{end+1} = {'o','place Object',  [0 0 1]         ,false,true};
        markers{end+1} = {'i','Idle',          [0 0 0],         true, false};
        markers{end+1} = {'a','Approach',      [0.03 0.46 0.73],true, true};
        markers{end+1} = {'s','Sniff',         [0.83 0.34 0.12],true, true};
        markers{end+1} = {'b','Bite',          [0.94 0.68 0.11],true, true};
        markers{end+1} = {'g','Grab',          [0.51 0.17 0.57],true, true};
        markers{end+1} = {'c','Carry',         [0.45 0.69 0.28],true, true};
        markers{end+1} = {'p','Push',          [0.65 0.39 0.28],true, true};
        markers{end+1} = {'v','aVoid',         [0.29 0.76 0.92],true, true};
        markers{end+1} = {'r','gRoom',         [0.1 0.5 0.8],   true, false};
        markers{end+1} = {'l','cLimb',         [0.8 0.2 0.9],   true, false};
    case 'looming'
        markers{end+1} = {'t','sTop stimulus',          [1 0 0],    false,true};
        markers{end+1} = {'h','start overHead stimulus',[0.4 0.2 1],false,true}; 
        markers{end+1} = {'i','Idle',                   [0 0 0],    true, false};
       % markers{end+1} = {'a','Approach',      [0.03 0.46 0.73],true, true};
       % markers{end+1} = {'s','Sniff',         [0.83 0.34 0.12],true, true};
       % markers{end+1} = {'b','Bite',          [0.94 0.68 0.11],true, true};
       % markers{end+1} = {'g','Grab',          [0.51 0.17 0.57],true, true};
       % markers{end+1} = {'c','Carry',         [0.45 0.69 0.28],true, true};
       % markers{end+1} = {'p','Push',          [0.65 0.39 0.28],true, true};
       % markers{end+1} = {'v','aVoid',         [0.29 0.76 0.92],true, true};
        markers{end+1} = {'r','gRoom',                  [0.1 0.5 0.8],   true, false};
        markers{end+1} = {'l','cLimb',                  [0.8 0.2 0.9],   true, false};
        markers{end+1} = {'e','Escape',                 [0.8 0.2 0.9],   true, false};
        markers{end+1} = {'f','Freeze',                 [0.8 0.2 0.9],   true, false};
        markers{end+1} = {'u','Rearing',                 [0.8 0.2 0.9],   true, false};
    case 'elevated_plus_maze'
        markers{end+1} = {'o','enter open arm',          [0 0 1],    true,false};
        markers{end+1} = {'c','enter closed arm',        [1 0 0],    true,false}; 
        markers{end+1} = {'m','enter middle',            [0 0 0],    true,false};
end
params.markers = cellfun( @(x) cell2struct(x,{'marker','description','color','behavior','linked'},2),markers);
params.nt_stop_marker = 't';
mask = (~[params.markers(:).behavior]) & [params.markers(:).linked];
params.nt_stim_markers = setdiff({params.markers(mask).marker},params.nt_stop_marker);
params.nt_show_markers = true; % false increases speed at the cost of information loss
params.nt_show_position_changes = true; % false reduces visual clutter at the cost of information loss
params.nt_show_overhead_mouse = true;


%% Analysis
params.automatically_track_mouse = false;

behaviors = {...
    {'run','running forward',[0 .7 0]},...
    {'turn_towards','turn towards object',[0 .7 0]},...
    {'leave_wall','leave wall',[0 0.7 0]},...
    {'retreat','retreating',[.7 0 0]},...
    {'turn_away','turn away from object',[.7 0 0]},...
    {'touch','touching object',[.7 .7 0]},...
    {'approach','approaching object',[0 .7 0]},...
    {'avoid','avoiding object',[.7 0 0]}  };
params.nt_behaviors = cellfun( @(x) cell2struct(x,{'behavior','description','color'},2),behaviors);

indices = { ...
    {'run_retreat_count_balance','run retreat count bal',[0 0 0]},...
    {'run_retreat_fraction_balance','run retreat frac bal',[0 0 0]},...
    {'turn_count_balance','turn count bal',[0 0 0]},...
    {'turn_fraction_balance','turn fraction bal',[0 0 0]}};
params.nt_indices = cellfun( @(x) cell2struct(x,{'index','description','color'},2),indices);

rates = {...
    {'forward_speed','Forward speed',[0 0 0]},...
    {'distance_to_wall','Distance to wall',[0 0 0]},...
    {'angular_velocity_towards_object','Rel. ang. velocity',[0 0 0]},...
    {'object_distance_derivative','\DeltaObject distance',[0 0 0]}};
params.nt_rates = cellfun( @(x) cell2struct(x,{'rate','description','color'},2),rates);

params.nt_max_touching_distance = 50; % mm
params.nt_min_run_speed = 90; % mm/s
params.nt_min_approach_speed = 90; % mm/s, change in object distance 
params.nt_min_retreat_speed = -70; % mm/s, note the minus sign
params.nt_min_angular_velocity = 100; % deg/s
params.nt_max_stationarity_speed = 15; % mm/s
params.nt_max_distance_to_wall = 115; % mm,  was 100 before diameter correction
params.nt_interaction_period = 10; % s, period to count interactions
params.nt_temporal_filter_width = 5; % neurotar samples
params.nt_object_sliding_window = 2.0; % s, window to use for peri-stimulus time averaging
params.count_once_per_object = true; % how often behaviours can be counter per interaction period

% Shuffle analysis
params.nt_seed = 1;
params.nt_shuffle_number = 10; 
params.nt_shuffle_insert_object_only_when_stationary = true;
params.nt_shuffle_stationary_period = 2; % s, period for which the animal has to be stationary to insert object

%% Fiber photometry

params.rwd_slack_time = 0.02; % time window for two events to be simultaneous
params.rwd_n_inputs = 5; % number of input channels
params.rwd_initial_input_state = NaN(1,params.rwd_n_inputs);
params.rwd_initial_input_state([1 2]) = [1 1];

params.nt_photometry_pretime = 10; % s
params.nt_photometry_posttime = 20; % s
params.nt_photometry_window_width = 0.1; % s
params.nt_photometry_bin_width = 0.250; % s

params.nt_apply_isosbestic_correction = false;

params.nt_color_gcamp = [0 0.8 0];
params.nt_color_isos = [0.2 0.2 1];



%% Results
params.nt_result_shows_individual_object_insertions = true;


%% Tracking
params.nt_show_behavior_markers = true;
params.nt_track_timeline_max_speed = 375; 
params.nt_show_help = false;
params.nt_show_bridge = true;
params.nt_show_horizon = true;
params.nt_show_boundaries = true; % neurotar frame 
params.nt_mouse_trace_window = 3; % s
params.nt_show_leave_wall_boundary = true;

if params.neurotar
    params.nt_show_distance_trace = true;
    params.nt_show_rotation_trace = true;
    params.nt_show_bridge = true;
    params.nt_show_horizon = true;
    params.nt_show_arena_panel = true;
else
    params.nt_show_distance_trace = false;
    params.nt_show_rotation_trace = false;
    params.nt_show_bridge = false;
    params.nt_show_horizon = false;
    params.nt_show_arena_panel = false;
end

%% Load processparams_local. Keep at the end
if exist('processparams_local.m','file')
    params = processparams_local( params );
end
