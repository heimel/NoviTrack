function nt_data = nt_load_DLC_data(record)
%nt_load_DLC_data. Loads pose data from DLC 
%
%    nt_data = nt_load_DLC_data(record)
%
%   Also see nt_load_mouse_tracks. Could be generalized
%
% 2025, Alexander Heimel

params = nt_default_parameters(record);

nt_data = [];
session_path = nt_session_path(record,params);

% 112212_20250523_001_overheadDLC_Resnet50_Foraging_behaviorMay26shuffle1_snapshot_110

filename = [ record.sessionid '_*DLC*.csv'];
filename = fullfile(session_path,filename);
d = dir(filename);
if isempty(d)
    % logmsg(['Cannot find DLC data for ' recordfilter(record)]);
    return
end
if length(d)>1
    logmsg(['Taking latest of multiple files with DLC data for ' recordfilter(record) ]);
end
filename = fullfile(session_path,d(end).name);

p = strfind(filename,'DLC_');
org_video_filename = [filename(1:p-1) '.mp4'];

% Read header rows (first 3 rows)
fid = fopen(filename, 'rt');
header1 = strsplit(fgetl(fid), ',');
header2 = strsplit(fgetl(fid), ',');
header3 = strsplit(fgetl(fid), ',');
fclose(fid);

% Combine headers into full variable names
nVars = length(header1);
varNames = cell(1, nVars);
for i = 1:nVars
    %varNames{i} = sprintf('%s_%s_%s', header1{i}, header2{i}, header3{i});
    varNames{i} = sprintf('%s_%s',  header2{i}, header3{i});
end

% Read numeric data, skipping the first 3 rows
data = readmatrix(filename, 'NumHeaderLines', 3);

% Optional: convert to table
dlc_table = array2table(data, 'VariableNames', matlab.lang.makeValidName(varNames));

% Example: access nose x-coordinates
nose_x = dlc_table.nose_x;
nose_y = dlc_table.nose_y;

% figure
% plot(nose_x,nose_y)


%nt_data.Time = extract_frametimes(org_video_filename)';

nt_data.X = dlc_table.nose_x;
nt_data.Y = dlc_table.nose_y;
if ismember('center_x',dlc_table.Properties.VariableNames)
    nt_data.CoM_X = dlc_table.center_x;
    nt_data.CoM_Y = dlc_table.center_y;
elseif ismember('center_point_x',dlc_table.Properties.VariableNames)
    nt_data.CoM_X = dlc_table.center_point_x;
    nt_data.CoM_Y = dlc_table.center_point_y;
end
if ismember('tail_base_x',dlc_table.Properties.VariableNames)
    nt_data.tailbase_X = dlc_table.tail_base_x;
    nt_data.tailbase_Y = dlc_table.tail_base_y;
elseif ismember('tail_x',dlc_table.Properties.VariableNames)
    nt_data.tailbase_X = dlc_table.tail_x;
    nt_data.tailbase_Y = dlc_table.tail_y;
end

logmsg('Loaded DLC data.')

% dt = mean(diff(nt_data.Time));
% overhead_mm_per_pixel = 0.5; % coarse estimate. 
% 
% nt_data.Speed = NaN(size(nt_data.CoM_X));
% nt_data.Speed(1:end-1) = sqrt(diff(nt_data.CoM_X).^2 + diff(nt_data.CoM_Y).^2) / dt * overhead_mm_per_pixel; 


% Still to implement
% nt_data.alpha = NaN(size(nt_data.X));
% nt_data.Forward_speed = NaN(size(nt_data.X));
% nt_data.Angular_velocity = NaN(size(nt_data.X)); 
% nt_data.Since_track_start = NaN(size(nt_data.X));
% nt_data.Distance_to_wall = NaN(size(nt_data.X));
% 

