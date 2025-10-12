function record = nt_import_markers(record)
% nt_import_markers. Imports varies log files with markers into record
%
%   RECORD = nt_import_markers(RECORD)
%
% 2025, Alexander Heimel

if isempty(record)
    return
end
if ~isfield(record,'measures')
    record.measures = struct([]); % Initialize measures field in record
end
if ~isfield(record.measures,'markers')
    record.measures.markers = struct([]);
end

import_options = {};
import_options{end+1} = {'Noldus EPM log','import_noldus_epm'};
import_options{end+1} = {'RWD log','import_rwd'};
import_options{end+1} = {'Laser log','import_laser'};

selections = nt_import_logs_dialog(import_options);

for i = 1:length(selections)
    ind = selections(i);
    disp( import_options{ind}{2})
    record = feval(import_options{ind}{2},record);
end

end

function record = import_laser(record)
% import prey laser and optogenetics log made on raspberry pi

params = nt_default_parameters(record);

[~,events] = nt_load_laser_triggers(record,[],params);
if isempty(events)
    return
end

markers = record.measures.markers;
for i = 1:length(events)
    time = events(i).time / params.laser_time_multiplier;
    duration = events(i).duration / params.laser_time_multiplier;
    switch events(i).code
        case 'p' % prey
            markers = nt_insert_marker(markers,time,'v',params);
            markers = nt_insert_marker(markers,time + duration,'t',params);
        case 'b' % both
            markers = nt_insert_marker(markers,time,'v',params);
            markers = nt_insert_marker(markers,time + duration,'t',params);
            markers = nt_insert_marker(markers,time,'1',params);
            markers = nt_insert_marker(markers,time + duration,'0',params);
        case 'o' % opto
            markers = nt_insert_marker(markers,time,'1',params);
            markers = nt_insert_marker(markers,time + duration,'0',params);
    end
end
record.measures.markers = markers;

end


function record = import_noldus_epm(record)
% import analysis xlsx from noldus epm analysis

events = nt_import_noldus_epm(record);
if isempty(events)
    return
end

offset_time = NaN;
while isnan(offset_time)
    time_prompt = 'Start time of analyzed movie:';
    time_input = inputdlg(time_prompt, 'Import Noldus EPM analysis', [1 50]);
    if isempty(time_input)
        time_input = '0';
    end
    offset_time = str2double(time_input{1});
end

% change to master time
% [events.time,~,multiplier] = nt_change_times(events.time,rwd_triggers1,record.measures.trigger_times) ;
% events.duration = events.duration * multiplier;

params = nt_default_parameters(record);
markers = record.measures.markers;
for i = 1:height(events)
    markers = nt_insert_marker(markers,offset_time + events.time(i),char(events.code(i)),params);
end
record.measures.markers = markers;
end


function record = import_rwd(record)
[rwd_triggers1,events] = nt_load_rwd_triggers(record);
if isempty(events)
    return
end

% change to master time
[events.time,~,multiplier] = nt_change_times(events.time,rwd_triggers1,record.measures.trigger_times) ;
events.duration = events.duration * multiplier;

% check if rwd trigger2 triggers match newstim triggers
[newstim_triggers,newstim_events] = nt_load_newstim_triggers(record);

rwd_stim_events = events(events.code=="Trigger2",:);

markers = record.measures.markers;
rwd_diff = diff(rwd_stim_events.time);
newstim_diff = diff(newstim_triggers(:));
if length(rwd_diff)==length(newstim_diff) && max(abs(rwd_diff-newstim_diff))<0.020
    % triggers are the same, using newstim stimuli
    for i = 1:height(newstim_events)
        time = rwd_stim_events.time(i);
        duration = newstim_events.duration(i);
        code = char(newstim_events.code(i));
        markers = nt_insert_marker(markers,time,code,params);
        markers = nt_insert_marker(markers,time+duration,['t' code(2)],params);
    end
else
    for i = 1:height(rwd_stim_events)
        time = rwd_stim_events.time(i);
        markers = nt_insert_marker(markers,time,'h1',params);
    end
end

record.measures.markers = markers;
end





function selections = nt_import_logs_dialog(import_options)
% IMPORT_DIALOG creates a dialog with 3 checkboxes and 2 buttons.
% Returns a logical vector [cb1, cb2, cb3] with checkbox states if 'Import' is pressed.
% Returns [] if 'Cancel' is pressed or window is closed.

button_height = 25;
button_sep = 5;
n_options = length(import_options);

height = (n_options+1)*button_height + (n_options+2)*button_sep;

% Create the dialog figure
dlg = dialog('Position',[500 400 250 height], 'Name','Import Options', 'WindowStyle','normal');

y = button_sep;
btn_import = uicontrol('Parent',dlg, 'Position',[30 y 80 30], 'String','Import', ...
    'Callback',@import_callback);

btn_cancel = uicontrol('Parent',dlg, 'Position',[140 y 80 30], 'String','Cancel', ...
    'Callback',@cancel_callback);

y = y + button_height + button_sep;


for i=1:n_options
    cb(i) = uicontrol('Parent',dlg, 'Style','checkbox', 'Position',[30 y 200 button_height], ...
        'String',import_options{i}{1},'Value',1);
    y = y + button_height + button_sep;
end


% Initialize output
selections = [];

% Wait for user response
uiwait(dlg);

% --- Callback functions ---
    function import_callback(~,~)
        % Return checkbox selections
        selections = find([cb(:).Value]);
        delete(dlg);
    end

    function cancel_callback(~,~)
        % Return empty
        selections = [];
        delete(dlg);
    end
end
