function [camera_x,camera_y] = nt_change_neurotar_to_camera_coordinates(neurotar_x,neurotar_y,params)
%nt_change_neurotar_to_camera_coordinates. Changes neurotar to overhead coordinates
%
%  [camera_x,camera_y] = nt_change_neurotar_to_camera_coordinates(neurotar_x,neurotar_y,params)
%
%   [neurotar_x, neurotar_y] (mm) are real world coordinates centered at
%       middle of neurotar setup, x is along bridge, y is orthogonal to
%       bridge, positive y is in front of the mouse
%
%   [camera_x, camera_y] (mm) are real world coordinates centered at camera
%   center, x is along image width, with the same increasing direction
%
%   [overhead_x, overhead_y] (pxl) are image coordinates x runs from 
%     (1:image_width) and y from (1:image_height) 
% 
% 2023-2024, Alexander Heimel

% swap direction of x-axis
neurotar_x = -neurotar_x;

% rotate axis to correct for camera rotation relative to neurotar
% ring = params.overhead_neurotar_headring - params.overhead_neurotar_center;
% alpha = angle( ring(2) + 1i*ring(1));

alpha = params.overhead_camera_angle;

rotation = [ cos(alpha) sin(alpha);-sin(alpha) cos(alpha)];
p = rotation * [neurotar_x; neurotar_y];

% invert overhead_center_position
[camera_neurotar_center_x, camera_neurotar_center_y] = ...
    nt_change_overhead_to_camera_coordinates(params.overhead_neurotar_center(1),params.overhead_neurotar_center(2),params);

% move center of neurotar to center position in camera coordinates
camera_x = p(1,:) + camera_neurotar_center_x;
camera_y = p(2,:) + camera_neurotar_center_y;

end