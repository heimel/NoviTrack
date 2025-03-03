function [neurotar_x,neurotar_y] = nt_change_arena_to_neurotar_coordinates(arena_x,arena_y,X,Y,alpha_deg,params)
%nt_change_arena_to_neurotar_coordinates. Changes from arena coordinates to real world coordinates
%
%   [neurotar_x,neurotar_y] = nt_change_arena_to_neurotar_coordinates(arena_x,arena_y,X,Y,alpha_deg,params)
%
%  Information about coordinates in neurotar_data_explanation.md
%  Snout distance as applied by Neurotar software can be computed by nt_compute_applied_snout_distance
% 
% 2023-2024, Alexander Heimel

alpha = alpha_deg/180*pi; % or a minus here?
rotation = [ cos(alpha) sin(alpha); -sin(alpha) cos(alpha)];
% p = [0; params.neurotar_snout_distance_mm] - rotation*[arena_x + X; arena_y + Y]; % OLD TRAFO

p = [0; params.neurotar_snout_distance_mm] + rotation*[arena_x - X; arena_y - Y];
neurotar_x = p(1,:) ;
neurotar_y = p(2,:);

end