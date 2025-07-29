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
        params.arena_open_arm_length_mm = 297;
        params.arena_open_arm_width_mm = 50;
        params.arena_closed_arm_length_mm = 300;
        params.arena_closed_arm_width_mm = 63;
        how = params.arena_open_arm_width_mm / 2;
        hcw = params.arena_closed_arm_width_mm / 2;
        ol = hcw + params.arena_open_arm_length_mm;
        cl = how + params.arena_closed_arm_length_mm;

        % arena_x = [ hw  hwl NaN hwl hw hw  -hw -hw -hwl NaN -hwl -hw -hw hw hw];
        % arena_y = [-hw -hw  NaN hw  hw hwl hwl hw   hw  NaN -hw  -hw -hwl -hwl -hw];
        arena_x = [ hcw ol NaN ol hcw hcw -hcw -hcw -ol NaN -ol -hcw -hcw hcw hcw];
        arena_y = [ -how -how NaN how how cl cl how how NaN -how -how -cl -cl -how];
end
