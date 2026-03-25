function [overhead_x,overhead_y] = nt_change_neurotar_to_overhead_coordinates(neurotar_x,neurotar_y,params)
%nt_change_neurotar_to_overhead_coordinates. Changes neurotar to overhead coordinates
%
% [OVERHEAD_X,OVERHEAD_Y] = nt_change_neurotar_to_overhead_coordinates(NEUROTAR_X,NEUROTAR_Y,PARAMS)
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

[camera_x, camera_y] = nt_change_neurotar_to_camera_coordinates(neurotar_x, neurotar_y, params);
[overhead_x, overhead_y] = nt_change_camera_to_overhead_coordinates(camera_x, camera_y, params);
end