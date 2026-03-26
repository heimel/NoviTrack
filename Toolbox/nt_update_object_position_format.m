function new_positions = nt_update_object_position_format(old_positions,params,record)
%nt_update_object_position_format Updates the format of the measures.object_positions 
%
%   new_positions = nt_update_object_position_format(old_positions,params,record)
%
%   format of object_positions: n x 5: time,x,y,coordinate system,object_id
%   format before 2023-08-08: n x 3: time,x,y [in params.ARENA coordinates]
%   format before 2024-07-26: n x 4: time,x,y,coordinate system
%
%   before 2024-07-26 virtual object locations were stored in params.NEUROTAR 
%   coordinates but this changed to OVERHEAD coordinates
%
% 2024, Alexander Heimel

if isempty(old_positions) 
    new_positions = [];
    return
end
if size(old_positions,2) == 3 % old format (changed on 2023-08-08)
    new_positions(:,4) = params.ARENA;
    new_positions(:,5) = 1; % object_id
    logmsg('Updated object positions in measures')
    return
end
if size(old_positions,2) < 3 || size(old_positions,2) > 4 
    errormsg('Unable to update object_positions',true);
end

n = size(old_positions,1);
new_positions = [old_positions ones(n,1)];

old_params = nt_default_parameters_20231201(record);

for i = 1:n
    if old_positions(i,4) == params.NEUROTAR
        [new_positions(i,2),new_positions(i,3)] = ...
            nt_change_neurotar_to_overhead_coordinates_20231201(old_positions(i,2),old_positions(i,3),record.measures,old_params);
        new_positions(i,4) = params.OVERHEAD;
    end
end

logmsg('Updated object positions in measures')

end

function params = nt_default_parameters_20231201(record)
% nt_default_parameters version from 2023-12-01

% General
params = struct;

params.networkpathbase = '\\vs03.herseninstituut.knaw.nl\VS03-CSF-1\Ren'; 

if nargin<1 || isempty(record.date) || datetime(record.date,'inputformat','yyyy-MM-dd') >  datetime('2023-11-03','inputformat','yyyy-MM-dd')
    % since about 2023-11-03
    params.overhead_camera_rotated = true;
    params.overhead_camera_pixels_per_mm  = 2.0;
    params.overhead_camera_distortion = 0.011; % Use 0 to remove distortion
    params.overhead_camera_shear = [0.90;0.90];
    params.overhead_camera_width = 752;
    params.overhead_camera_height = 550;
    params.overhead_neurotar_headring_default = [275; 322]; % position of center of headring in overhead image
    params.overhead_neurotar_center_default = [256; 238];  % position of center of bar in overhead image
end

if nargin<1 || isempty(record.date) || datetime(record.date,'inputformat','yyyy-MM-dd') >  datetime('2023-06-21','inputformat','yyyy-MM-dd') & datetime(record.date,'inputformat','yyyy-MM-dd') <  datetime('2023-11-03','inputformat','yyyy-MM-dd')
    % since about 2023-06-21
    params.overhead_camera_rotated = true;
    params.overhead_camera_pixels_per_mm  = 2.0;
    params.overhead_camera_distortion = 0.0045; % Use 0 to remove distortion
    params.overhead_camera_shear = [0.99;0.99];
    params.overhead_camera_width = 752;
    params.overhead_camera_height = 582;
    params.overhead_neurotar_headring_default = [275; 322]; % position of center of headring in overhead image
    params.overhead_neurotar_center_default = [256; 238];  % position of center of bar in overhead image
end

if nargin<1 || isempty(record.date) || datetime(record.date,'inputformat','yyyy-MM-dd') <  datetime('2023-06-21','inputformat','yyyy-MM-dd') 
    % before 2023-06-21
    params.overhead_camera_rotated = true;
    params.overhead_camera_pixels_per_mm  = 2.0;
    % params.overhead_camera_rotation_deg = -8; % Deprecated
    params.overhead_camera_distortion = 0.003; % Use 0 to remove distortion
    %params.overhead_camera_shear = [1.15;1.35];
    params.overhead_camera_shear = [1.15;1.15];
    params.overhead_camera_width = 752;
    params.overhead_camera_height = 582;
    params.overhead_neurotar_headring_default = [275; 322]; % position of center of headring in overhead image
    params.overhead_neurotar_center_default = [256; 238];  % position of center of bar in overhead image
end

params.neurotar_snout_distance_mm = 45; % mm distance from snout to center of neurotar
params.arena_radius_mm = 162.5; % mm  (was 145 mm)
params.neurotar_halfwidth_mm = 260;

markers = { ...
    {'o','start physical stimulus',[0 0 1],false} , ... % e.g. object
    {'v','start virtual stimulus',[0 1 0],false} , ... % e.g. laser
    {'i','start IR virtual stimulus',[1 0.5 0],false} , ... % e.g. control laser
    {'h','start hanging physical stimulus',[0.4 0.2 1],false},... % e.g. finger or hanging object
    {'t','stop stimulus',[1 0 0],false},...
    {'e','end session',[0 0 0],false},...  % e.g. mouse removed
    {'a','begin approach object',[0 0.7 0],true}, ...
    {'r','begin retreat from object',[0.7 0 0],true}} ; 
params.markers = cellfun( @(x) cell2struct(x,{'marker','description','color','behavior'},2),markers);

% align times at trigger and then multiply master time with specific
% multiplier to obtain time in [picamera] values
params.picamera_time_multiplier = 1.0006;  

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

end


function [overhead_x,overhead_y] = nt_change_neurotar_to_overhead_coordinates_20231201(neurotar_x,neurotar_y,measures,params)
%nt_change_neurotar_to_overhead_coordinates version from 2023-12-01

% adjust scale
x = -neurotar_x * params.overhead_camera_pixels_per_mm;
y =  neurotar_y * params.overhead_camera_pixels_per_mm;

% rotate axis to correct for camera rotation relative to neurotar
ring = measures.overhead_neurotar_headring - measures.overhead_neurotar_center;
alpha = angle( ring(2) + 1i*ring(1));
rotation = [ cos(alpha) sin(alpha);-sin(alpha) cos(alpha)];
p = rotation * [x;y];

% invert overhead_center_position
cp = nt_undistort_overhead_20230616(measures.overhead_neurotar_center(:),params);

% move center of neurotar to center position in camera coordinates
p = p + cp;

% distort by camera lense
p = nt_distort_overhead_20230616(p,params);
overhead_x = p(1,:);
overhead_y = p(2,:);
end

function p = nt_undistort_overhead_20230616(p,params)
% version from 2023-06-16
par = params.overhead_camera_distortion;
p = p .* params.overhead_camera_shear;
p = p - [params.overhead_camera_width; params.overhead_camera_height]/2;
[theta,rho] = cart2pol(p(1,:),p(2,:));
rho = (exp(rho*par)-1)/par;
[x,y] = pol2cart(theta,rho);
p = [x;y] + [params.overhead_camera_width; params.overhead_camera_height]/2;
end

function p = nt_distort_overhead_20230616(p,params)
% version from 2023-06-16
par = params.overhead_camera_distortion;
p = p - [params.overhead_camera_width; params.overhead_camera_height]/2;
[theta,rho] = cart2pol(p(1,:),p(2,:));
rho = log(rho*par+1)/par;
[x,y] = pol2cart(theta,rho);
p = [x;y] + [params.overhead_camera_width; params.overhead_camera_height]/2;
p = p ./ params.overhead_camera_shear;
end