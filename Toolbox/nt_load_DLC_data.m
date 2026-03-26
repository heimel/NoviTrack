function nt_data = nt_load_DLC_data(record)
%nt_load_DLC_data. Loads pose data from DLC 
%
%    nt_data = nt_load_DLC_data(record)
%
%   Also see nt_load_tracking_data. 
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
    return
end
if length(d)>1
    logmsg(['Taking latest of multiple files with DLC data for ' recordfilter(record) ]);
end
filename = fullfile(session_path,d(end).name);

p = strfind(filename,'DLC_');

fid = fopen(filename, 'rt');
header1 = strsplit(fgetl(fid), ',');
header2 = strsplit(fgetl(fid), ',');
header3 = strsplit(fgetl(fid), ',');
fclose(fid);

% Combine headers into full variable names
nVars = length(header1);
varNames = cell(1, nVars);
for i = 1:nVars
    varNames{i} = sprintf('%s_%s',  header2{i}, header3{i});
end

data = readmatrix(filename, 'NumHeaderLines', 3);
dlc_table = array2table(data, 'VariableNames', matlab.lang.makeValidName(varNames));

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

nt_data.Coordinates = params.OVERHEAD;

logmsg('Loaded DLC data.')

