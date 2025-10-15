function record = nt_add_surgery_info(record)
%nt_add_surgery_info. Add (fiber) info from surgery sheet to measures
%
%  record = nt_add_surgery_info(record)
%
% 2025, Alexander Heimel

folder = fullfile(nt_session_path(record),'..','..','Surgery_logs');
filename = fullfile(folder,'Surgery_sites.xlsx');

if ~exist(filename,'file')
    logmsg(['Cannot find surgery log for ' recordfilter(record)]);
    return
end

surgery_table = readtable(filename, 'Sheet', 'Sheet1','TextType','string');

ind = find(surgery_table.subject == "#"+record.subject);
if isempty(ind)
    ind = find(surgery_table.subject == "#0"+record.subject);
end
if isempty(ind)
    logmsg(['Could not find mouse #' record.subject ' in Surgery_sitex.xlsx']);
    return
end
if length(ind)>1
    logmsg(['More than one mouse #' record.subject ' in Surgery_sitex.xlsx']);
    return
end
surgery_table = surgery_table(ind,:);

record.measures.strain = surgery_table.strain;
record.measures.surgery_comment = surgery_table.comment;

if ~isempty(surgery_table.fiber1_location)
    fiber_info.fiber1.hemisphere = surgery_table.fiber1_hemisphere;
    fiber_info.fiber1.location = surgery_table.fiber1_location;
    if ismember('fiber1_green',surgery_table.Properties.VariableNames)
        fiber_info.fiber1.green_sensor = surgery_table.fiber1_green;
    else
        fiber_info.fiber1.green_sensor = '';
    end
    if ismember('fiber1_red',surgery_table.Properties.VariableNames)
        fiber_info.fiber1.red_sensor = surgery_table.fiber1_red;
    else
        fiber_info.fiber1.red_sensor = '';
    end
end
if ~isempty(surgery_table.fiber2_location)
    fiber_info.fiber2.hemisphere = surgery_table.fiber2_hemisphere;
    fiber_info.fiber2.location = surgery_table.fiber2_location;
    if ismember('fiber2_green',surgery_table.Properties.VariableNames)
        fiber_info.fiber2.green_sensor = surgery_table.fiber2_green;
    else
        fiber_info.fiber2.green_sensor = '';
    end
    if ismember('fiber2_red',surgery_table.Properties.VariableNames)
        fiber_info.fiber2.red_sensor = surgery_table.fiber2_red;
    else
        fiber_info.fiber2.red_sensor = '';
    end
end

record.measures.fiber_info = fiber_info;

