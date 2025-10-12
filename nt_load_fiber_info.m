function record = nt_load_fiber_info(record)
%nt_load_fiber_info. Reads fiber info from surgery sheet
%
%  record = nt_load_fiber_info(record)
%
% 2025, Alexander Heimel

folder = fullfile(nt_session_path(record),'..','..','Surgery');
filename = fullfile(folder,'Surgery_sites.xlsx');
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
        fiber_info.fiber1.green = surgery_table.fiber1_green;
    end
    if ismember('fiber1_red',surgery_table.Properties.VariableNames)
        fiber_info.fiber1.red = surgery_table.fiber1_red;
    end
end
if ~isempty(surgery_table.fiber2_location)
    fiber_info.fiber2.hemisphere = surgery_table.fiber2_hemisphere;
    fiber_info.fiber2.location = surgery_table.fiber2_location;
    if ismember('fiber2_green',surgery_table.Properties.VariableNames)

        fiber_info.fiber2.green = surgery_table.fiber2_green;
    end
    if ismember('fiber2_red',surgery_table.Properties.VariableNames)

        fiber_info.fiber2.red = surgery_table.fiber2_red;
    end
end

record.measures.fiber_info = fiber_info;

