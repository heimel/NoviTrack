function nt_update_arena_walls(handle,state,params)
% nt_update_arena_walls. Update line plot in overhead coordinates with arena walls
%
%     nt_update_arena_walls(handle,state,params)
%
% 2025, Alexander Heimel

[arena_x,arena_y] = nt_arena_walls(params);

if params.neurotar
    [neurotar_x,neurotar_y] = nt_change_arena_to_neurotar_coordinates(...
        0,0,state.X,state.Y,state.alpha,params);
    arena_x = arena_x + neurotar_x;
    arena_y = arena_y + neurotar_y;
    [handle.XData,handle.YData] = nt_change_neurotar_to_overhead_coordinates(arena_x,arena_y,params);
else
    [handle.XData,handle.YData] = nt_change_arena_to_overhead_coordinates(arena_x,arena_y,[],[],[],params);
end