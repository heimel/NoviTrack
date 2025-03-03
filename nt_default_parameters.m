function params = nt_default_parameters(record)
%nt_default_paramters Contains default parameters for neurotar analysis
%
%  PARAM = nt_default_parameters([RECORD])
%
%  Edit processparams_local for local and temporary edits to these default
%  parameters.
%
% 2023-2024, Alexander Heimel 

if nargin<1 
    record = [];
end

% General
params = struct;

% Constants
params.ARENA = 1;
params.NEUROTAR = 2;
params.CAMERA = 3;
params.OVERHEAD = 4; 

% Data storage
params.networkpathbase = '\\vs03.herseninstituut.knaw.nl\VS03-CSF-1\Ren'; 

% Communication between Pi's 
params.root_communication_path = '\\VS03\VS03-CSF-1\Communication';

% Debugging and testing 
params.nt_debug = false;

% User interface
params.fontsize = 8; % pt

% For faster graphics
params.nt_graphicssmoothing = 'off';
params.nt_renderer = 'opengl'; % Matlab default is 'opengl'. On some computers 'painters' could be quicker
params.nt_drawnow_limitrate = false;

params.nt_camera_names = {'pilefteye','pioverhead','pirighteye'};
params.nt_overhead_camera = 2;

% placeholder values that are overwritten by actual values
params.overhead_camera_width = 752;
params.overhead_camera_height = 550;
params.overhead_camera_distortion_method = 'fisheye_orthographic';
params.overhead_camera_distortion = [339 339];         
% distortion(1) = distance_neurotar_center_to_camera_mm
% distortion(2) = focal_distance_pxl
params.overhead_camera_angle = -0.13;
params.overhead_camera_rotated = true;
params.neurotar_snout_distance_mm = 32;
params.overhead_neurotar_headring = [275; 322]; % position of center of headring in overhead image


if nargin<1 || isempty(record.date) || datetime(record.date,'inputformat','yyyy-MM-dd') >  datetime('2023-11-03','inputformat','yyyy-MM-dd')
    % since about 2023-11-03
    params.overhead_camera_rotated = true;
    % params.overhead_camera_pixels_per_mm  = 2.0;
    % params.overhead_camera_distortion_method = 'fisheye_log';
    % params.overhead_camera_distortion = 0.011; % Use 0 to remove distortion
    % params.overhead_camera_shear = [0.90;0.90];
    % params.overhead_neurotar_headring = [275; 322]; % position of center of headring in overhead image
    params.overhead_neurotar_center = [256; 238];  % position of center of bar in overhead image
    params.neurotar_snout_distance_mm = 32; % distance from snout to center of neurotar
end

if nargin<1 || isempty(record.date) || datetime(record.date,'inputformat','yyyy-MM-dd') <  datetime('2023-06-21','inputformat','yyyy-MM-dd') 
    % before 2023-06-21
    params.overhead_camera_rotated = true;
    % params.overhead_camera_pixels_per_mm  = 2.0;
    % params.overhead_camera_distortion_method = 'fisheye_log';
    % params.overhead_camera_distortion = 0.003; % Use 0 to remove distortion
    % params.overhead_camera_shear = [1.15;1.15];
    % params.overhead_neurotar_headring = [275; 322]; % position of center of headring in overhead image
    params.overhead_neurotar_center = [256; 238];  % position of center of bar in overhead image
    params.neurotar_snout_distance_mm = 0; % distance from snout to center of neurotar
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

%params.neurotar_snout_distance_mm = 45; % distance from snout to center of neurotar
params.arena_radius_mm = 162.5; %  
params.neurotar_halfwidth_mm = 260;

markers = { ...
    {'o','start physical stimulus',[0 0 1],false} , ... % e.g. object
    {'v','start virtual stimulus',[0 1 0],false} , ... % e.g. laser
    {'i','start IR virtual stimulus',[1 0.5 0],false} , ... % e.g. control laser
    {'h','start hanging physical stimulus',[0.4 0.2 1],false},... % e.g. finger or hanging object
    {'t','stop stimulus',[1 0 0],false},...
    {'e','end session',[0 0 0],false},...  % e.g. mouse removed
    {'1','optolaser on',[0 0 1],false},...  % e.g. optogenetics laser on
    {'0','optolaser off',[0 0 0],false},...  % e.g. optogenetics laser off
    {'a','begin approach object',[0 0.7 0],true}, ...
    {'r','begin retreat from object',[0.7 0 0],true}} ; 
params.markers = cellfun( @(x) cell2struct(x,{'marker','description','color','behavior'},2),markers);
params.nt_stimulus_types = {'o','v','i','h'};

% Analysis
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

% Results
params.nt_result_shows_individual_object_insertions = true;

% Tracking
params.nt_show_behavior_markers = false;
params.nt_track_timeline_max_speed = 375; 
params.nt_show_help = false;
params.nt_show_bridge = true;
params.nt_show_horizon = true;
params.nt_mouse_trace_window = 3; % s
params.nt_show_leave_wall_boundary = true;

% Load processparams_local. Keep at the end
if exist('processparams_local.m','file')
    params = processparams_local( params );
end
