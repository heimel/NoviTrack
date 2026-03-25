function mask = nt_arena_mask(record)
%nt_arena_mask. Makes an logical mask with arena true
%
%   MASK = nt_arena_mask(RECORD)
%
% 2025, Alexander Heimel

params = nt_default_parameters(record);

arena_x = [-1  1 1 -1 -1]*params.arena_diameter_mm/2; % mm
arena_y = [-1 -1 1  1 -1]*params.arena_diameter_mm/2; % mm

mask = false(params.overhead_camera_height,params.overhead_camera_width);
[X,Y] = meshgrid(1:params.overhead_camera_height,1:params.overhead_camera_width);

[x,y] = nt_change_arena_to_overhead_coordinates(arena_x,arena_y,[],[],[],params);

%mask = inpolygon(X,Y,x,y)';
mask = inpolygon(X,Y,y,x)';
%mask = mask(end:-1:1,:);
