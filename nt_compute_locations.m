function record = nt_compute_locations(record,nt_data,verbose)
% nt_compute_locations. Compute and show measurements based on location
%
%    record = nt_compute_locations(record,nt_data)
%
% 2025, Alexander Heimel

if nargin<3 || isempty(verbose)
    verbose = true;
end
if nargin<2 || isempty(nt_data)
    nt_data = nt_load_neurotar_data(record);
    if isempty(nt_data)
        nt_data = nt_load_mouse_tracks(record);
    end
end

params = nt_default_parameters(record);
measures = record.measures;

[arena_x,arena_y] = nt_change_overhead_to_arena_coordinates(nt_data.CoM_X',nt_data.CoM_Y',[],[],[],params);
[arena_walls_x,arena_walls_y] = nt_arena_walls(params);
center_x = (params.arena_radius_mm -params.nt_max_distance_to_wall)/params.arena_radius_mm * arena_walls_x;
center_y = (params.arena_radius_mm -params.nt_max_distance_to_wall)/params.arena_radius_mm * arena_walls_y;
in_center = inpolygon(arena_x,arena_y,center_x,center_y);

measures.frac_in_center = sum(in_center)/length(in_center);

% compute distance from wall?

% check that the body is always in arena
in_arena = inpolygon(arena_x,arena_y,arena_walls_x,arena_walls_y);
measures.frac_out_off_arena = sum(~in_arena)/length(in_arena);

if verbose
    figure;
    subplot(2,2,1)
    title('C.o.M.');
    hold on
    plot(arena_x,arena_y,'.r')
    line(arena_walls_x,arena_walls_y)
    line(center_x,center_y)
    plot(arena_x(in_center),arena_y(in_center),'.k');
    axis square
end

record.measures = measures;