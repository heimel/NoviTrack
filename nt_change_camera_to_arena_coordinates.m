function [arena_x,arena_y] = nt_change_camera_to_arena_coordinates(camera_x,camera_y,params)

if params.neurotar
    errormsg('NOT IMPLEMENTED YET');
end

% invert overhead_center_position
[camera_neurotar_center_x, camera_neurotar_center_y] = ...
    nt_change_overhead_to_camera_coordinates(params.overhead_neurotar_center(1),params.overhead_neurotar_center(2),params);

% move center of neurotar to center position in camera coordinates
camera_x = camera_x - camera_neurotar_center_x;
camera_y = camera_y - camera_neurotar_center_y;

% rotate axis to correct for camera rotation relative to neurotar
% ring = params.overhead_neurotar_headring - params.overhead_neurotar_center;
% alpha = -angle( ring(2) + 1i*ring(1));
alpha = -params.overhead_camera_angle;
rotation = [ cos(alpha) sin(alpha);-sin(alpha) cos(alpha)];
p = rotation * [camera_x; camera_y];

arena_x = p(1,:);
arena_y = p(2,:);

% swap direction of x-axis
%neurotar_x = -neurotar_x;
