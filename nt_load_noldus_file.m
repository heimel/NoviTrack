function tbl = nt_load_noldus_file(record)
% nt_load_noldus_file. Loads Noldus analysis xlsx file
%
%    tbl = nt_load_noluds_tracking(record)
%
%      tbl.VideoTime contains time from start of video (s)
%
% 2025, Alexander Heimel

tbl = [];

params = nt_default_parameters(record);

folder = nt_session_path(record);
file_pattern = [record.subject '_Noldus_behavioral_data.xlsx'];
d = dir(fullfile(folder,file_pattern));

if isempty(d)
    logmsg(['Cannot find Noldus analysis file in ' folder ]);
    logmsg(['Looking for "' file_pattern '"'])
    return
end
if length(d)>1
    logmsg(['More than one Noldus analysis file in ' folder ]);
    logmsg('Remove or rename additional files');
    return
end
filename = fullfile(folder, d(1).name);
sheetname = 'Track-Arena 1-Subject 1';

warning('off','MATLAB:table:ModifiedAndSavedVarnames');
raw = readcell(filename,'Sheet',sheetname);
nonEmptyRows = find(any(~cellfun(@(x) isempty(x) || (isstring(x) && strlength(x)==0), raw), 2));
lastRow = nonEmptyRows(end);

% parse header
ind = find(contains(raw(1:10,1),'Number of header lines:'));
n_header_lines = str2num(raw{ind,2});
row_variable_names = n_header_lines - 1; 
row_unit_names = n_header_lines ; 

ind = find(contains(raw(1:n_header_lines,1),'Animal ID'));
animal_id = raw{ind,2};

if ~strcmp(record.subject,animal_id)
    logmsg(['Warning: Record subject ' record.subject ' and Noldus animal_id ' animal_id ' are not identical.']);
end

ind = find(contains(raw(1:n_header_lines,1),'Video start time'));
video_start_time = raw{ind,2}; % e.g. '08/10/2025 13:21:17'

ind = find(contains(raw(1:n_header_lines,1),'Start time'));
trial_start_time = raw{ind,2}; % e.g. '08/10/2025 13:22:06'

try
    video_start_time_dt = datetime(video_start_time, 'InputFormat', 'dd/MM/yyyy HH:mm:ss');
    trial_start_time_dt = datetime(trial_start_time, 'InputFormat', 'dd/MM/yyyy HH:mm:ss');
catch me
    switch me.identifier
        case  'MATLAB:datetime:ParseErr'
            video_start_time_dt = datetime(video_start_time, 'InputFormat', 'dd-MM-yyyy HH:mm:ss');
            trial_start_time_dt = datetime(trial_start_time, 'InputFormat', 'dd-MM-yyyy HH:mm:ss');
    end
end
time_offset = seconds(trial_start_time_dt - video_start_time_dt); % in seconds

opts = detectImportOptions(filename);
opts.VariableNamesRange = [num2str(row_variable_names) ':' num2str(row_variable_names)];%  '35:35';   % headers at row 36
opts.DataRange = sprintf('37:%d', lastRow); % data starts at row 38

tbl = readtable(filename, opts,'Sheet',sheetname);
tbl.VideoTime = tbl.TrialTime + time_offset;

warning('on','MATLAB:table:ModifiedAndSavedVarnames');
