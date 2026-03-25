function [camera_x, camera_y] = nt_change_arena_to_camera_coordinates(arena_x, arena_y, params)
%nt_change_arena_to_camera. Changes arena coordinates to real world camera centered coordinates 
%
%  [camera_x, camera_y] = nt_change_arena_to_camera_coordinates(arena_x, arena_y, params)
%
% 2025, Alexander Heimel

if params.neurotar
    errormsg('NOT IMPLEMENTED YET');
end

if isempty(arena_x) || isempty(arena_y)
    camera_x = [];
    camera_y = [];
    return
end


%% Fixed arena

% swap direction of x-axis
%arena_x = -arena_x;

% rotate axis to correct for camera rotation relative to neurotar
% ring = params.overhead_neurotar_headring - params.overhead_neurotar_center;
% alpha = angle( ring(2) + 1i*ring(1));

alpha = params.overhead_camera_angle;

rotation = [ cos(alpha) sin(alpha);-sin(alpha) cos(alpha)];
p = rotation * [arena_x; arena_y];

% invert overhead_center_position
[camera_arena_center_x, camera_arena_center_y] = ...
    nt_change_overhead_to_camera_coordinates(params.overhead_arena_center(1),params.overhead_arena_center(2),params);

% move center of neurotar to center position in camera coordinates
camera_x = p(1,:) + camera_arena_center_x;
camera_y = p(2,:) + camera_arena_center_y;
