function [arena_x,arena_y] = nt_change_overhead_to_arena_coordinates(overhead_x,overhead_y,X,Y,alpha_deg,params)
%nt_change_overhead_to_arena_coordinates Changes from overhead coordinates in pixels to arena coordinates in mm
%
%   [arena_x,arena_y] = nt_change_overhead_to_arena_coordinates(overhead_x,overhead_y,X,Y,alpha_deg,params)
% 
% 2024-2025, Alexander Heimel

if params.neurotar
    [neurotar_x,neurotar_y] = nt_change_overhead_to_neurotar_coordinates(overhead_x,overhead_y,params);
    [arena_x,arena_y] = nt_change_neurotar_to_arena_coordinates(neurotar_x,neurotar_y,X,Y,alpha_deg,params);
else
    [camera_x, camera_y] = nt_change_overhead_to_camera_coordinates(overhead_x,overhead_y,params);
    [arena_x,arena_y] = nt_change_camera_to_arena_coordinates(camera_x,camera_y,params);
end

end