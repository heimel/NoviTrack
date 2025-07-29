function [arena_x,arena_y] = nt_arena_walls(params)
%nt_arena_walls. Returns arena coordinates of the walls
%
%     [arena_x,arena_y] = nt_arena_walls(params)
%
% 2025, Alexander Heimel

switch params.arena_shape
    case 'circular'
        theta = 0:pi/15:2*pi;
        arena_x = params.arena_radius_mm * sin(theta);
        arena_y = params.arena_radius_mm * cos(theta);
    case 'square'
        arena_x = [-1  1 1 -1 -1]*params.arena_diameter_mm/2; % mm
        arena_y = [-1 -1 1  1 -1]*params.arena_diameter_mm/2; % mm
    case 'plus'
        arena_x = [-1  1 1 -1 -1]*params.arena_diameter_mm/2; % mm
        arena_y = [-1 -1 1  1 -1]*params.arena_diameter_mm/2; % mm
end
