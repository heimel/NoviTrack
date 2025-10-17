function nt_data = nt_load_noldus_tracking(record)
% nt_load_noldus_tracking. Loads tracking data from Noldus analysis xlsx
%
%    nt_data = nt_load_noluds_tracking(record)
%       Time: [n_samples×1 double]  in seconds
%       CoM_X: [n_samples×1 double]  center of mass, X
%       CoM_Y: [n_samples×1 double]  center of mass, Y
%       Speed: [n_samples×1 double] in m/s
%
% 2025, Alexander Heimel

nt_data = [];

params = nt_default_parameters(record);


tbl = nt_load_noldus_file(record);

if isempty(tbl)
    return
end

nt_data.Time = tbl.VideoTime;
nt_data.CoM_X = tbl.XCenter;
nt_data.CoM_Y = tbl.YCenter;
nt_data.Speed = tbl.Velocity * 0.01; % converting to m/s


