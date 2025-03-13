function nt_update_arena_walls(handle,state,params)


if params.neurotar
    theta = 0:pi/15:2*pi;
    [neurotar_x,neurotar_y] = nt_change_arena_to_neurotar_coordinates(...
        0,0,state.X,state.Y,state.alpha,params);
    neurotar_x = neurotar_x + params.arena_radius_mm * sin(theta) ;
    neurotar_y = neurotar_y + params.arena_radius_mm * cos(theta) ;
    [handle.XData,handle.YData] = nt_change_neurotar_to_overhead_coordinates(neurotar_x,neurotar_y,params);
else
    arena_x = [-1  1 1 -1 -1]*params.arena_diameter_mm/2; % mm
    arena_y = [-1 -1 1  1 -1]*params.arena_diameter_mm/2; % mm
    [handle.XData,handle.YData] = nt_change_arena_to_overhead_coordinates(arena_x,arena_y,[],[],[],params);
end