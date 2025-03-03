function [arena_x,arena_y] = nt_change_neurotar_to_arena_coordinates(neurotar_x,neurotar_y,X,Y,alpha_deg,params)
%nt_change_neurotar_to_arena_coordinates. Changes neurotar to arena coordinates
%
% [ARENA_X,ARENA_Y] = nt_change_neurotar_to_arena_coordinates(NEUROTAR_X,NEUROTAR_Y,X,Y,ALPHA_DEG,PARAMS)
%
%  Check neurotar_data_explanation.md for more information about neurotar
%  coordinate system.
%
% 2023-2024, Alexander Heimel

alpha = -alpha_deg/180*pi;
rotation = [ cos(alpha) sin(alpha);-sin(alpha) cos(alpha)];
%p = -[X;Y] - rotation * [neurotar_x;neurotar_y - params.neurotar_snout_distance_mm]; % OLD TRAFO
p = [X;Y] + rotation * [neurotar_x;neurotar_y - params.neurotar_snout_distance_mm];
arena_x = p(1,:);
arena_y = p(2,:);

end