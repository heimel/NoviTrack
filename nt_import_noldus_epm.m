function events = nt_import_noldus_epm(record)
% nt_import_noldus_epm. Imports markers from Noldus elevated plus maze analysis
%
%     EVENTS = nt_import_noldus_epm(RECORD)
%
%        EVENTS is table with fields: time, code, duration
%              code = 'o','c','m' for entering open arm, close arm, or
%              center, respectively.
%              time is on Noldus EPM clock
%
% 2025, Alexander Heimel

events = struct([]);

file_pattern = 'Raw data-elevated_plus_maze-Trial*.xlsx';
folder = nt_session_path(record);

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

raw = readcell(filename);
nonEmptyRows = find(any(~cellfun(@(x) isempty(x) || (isstring(x) && strlength(x)==0), raw), 2));
lastRow = nonEmptyRows(end);

opts = detectImportOptions(filename);
opts.VariableNamesRange = '35:35';   % headers at row 36
opts.DataRange = sprintf('37:%d', lastRow); % data starts at row 38

tbl = readtable(filename, opts);

logmsg('NOT SURE YET IF I NEED TO USE TRIALTIME OR RECORDINGTIME. CHECK');

center_times = tbl.TrialTime(find(diff(tbl.InZone_Center_Center_point_)>0)+1);
closed_times = tbl.TrialTime(find(diff(tbl.InZone_ClosedArms_Center_point_)>0)+1);
open_times = tbl.TrialTime(find(diff(tbl.InZone_OpenArms_Center_point_)>0)+1);
all_times = sort([center_times;closed_times;open_times]);

n_events = length(all_times);
events = table('Size', [n_events, 3], 'VariableTypes', {'double', 'string', 'double'}, ...
               'VariableNames', {'time', 'code', 'duration'});

all_times(end+1) = NaN;
for i = 1:n_events
    time = all_times(i);
    if ismember(all_times(i),center_times)
        code = "m";
    elseif ismember(all_times(i),closed_times)
        code = "c";
    else 
        code = "o";
    end
    duration = all_times(i+1) - all_times(i);
    
    events(i,:) = table(time, code, duration);
end
