function [neurotar_x,neurotar_y] = nt_change_overhead_to_neurotar_coordinates(overhead_x, overhead_y, params)
%nt_change_overhead_to_neurotar_coordinates. Changes overhead to neurotar coordinates
%
%   [neurotar_x,neurotar_y] = nt_change_overhead_to_neurotar_coordinates(overhead_x, overhead_y, params)
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

[camera_x, camera_y] = nt_change_overhead_to_camera_coordinates(overhead_x, overhead_y, params);
[neurotar_x, neurotar_y] = nt_change_camera_to_neurotar_coordinates(camera_x, camera_y, params);



