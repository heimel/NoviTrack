function [overhead_x,overhead_y] = nt_change_arena_to_overhead_coordinates(arena_x,arena_y,X,Y,alpha_deg,params)
%nt_change_arena_to_overhead_coordinates Changes from arena coordinates to real world neurotar coordinates
%
% [overhead_x,overhead_y] = nt_change_arena_to_overhead_coordinates(arena_x,arena_y,X,Y,alpha_deg,params)
% 
% 2023-2024, Alexander Heimel

if params.neurotar
    [neurotar_x, neurotar_y] = nt_change_arena_to_neurotar_coordinates(arena_x,arena_y,X,Y,alpha_deg,params);
    [overhead_x, overhead_y] = nt_change_neurotar_to_overhead_coordinates(neurotar_x,neurotar_y,params);
else
    [camera_x, camera_y] = nt_change_arena_to_camera_coordinates(arena_x,arena_y,params);
    [overhead_x, overhead_y] = nt_change_camera_to_overhead_coordinates(camera_x, camera_y, params);
end

end