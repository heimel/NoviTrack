function [triggers,events] = nt_load_rwd_triggers(record)
%nt_load_rwd_triggers. Loads events file from RWD fiber photometer
%
%  [TRIGGERS,EVENTS] = nt_load_rwd_triggers(RECORD)
%        TRIGGERS in seconds is on RWD clock
%        EVENTS is table with fields: time, code, duration
%            time is on RWD clock
%
% 2025, Alexander Heimel

params = nt_load_parameters( record );

triggers = [];
events = [];

[folder,found] = nt_photometry_folder(record);
if ~found
    return
end

events = readtable(fullfile(folder, "Events.csv"));
events.Name = categorical(events.Name);
events.TimeStamp = events.TimeStamp/1000; % change to s

prev_state = params.rwd_initial_input_state;
events = convert_event_rwd(events, prev_state, params.rwd_slack_time);

triggers = events.time(string(events.code) == "Trigger1");

if isempty(triggers)
    logmsg('No triggers found on Input1')
    if ~isempty(events)
        logmsg('But there are events on other inputs')
    end
    return
end

end

function out_table = convert_event_rwd(event_rwd, prev_state, slack_time)
input_names = {"Input1", "Input2","Input3","Input4","Input5"};
trigger_names = {"Trigger1","Trigger2","Trigger3","Trigger4","Trigger5"};

% Preallocate output
out = struct('time', {}, 'code', {}, 'duration', {});

for i = 1:length(input_names)
    input_name = input_names{i};
    trigger_name = trigger_names{i};
    state = prev_state(i);

    % Extract events for this input
    idx = (event_rwd.Name==input_name );
    times = event_rwd.TimeStamp(idx);
    states = event_rwd.State(idx);

    j = 1;
    while j <= length(states)
        if ~isnan(state) && states(j) == state
            j = j + 1; % duplicate line or unchanged initial state
            continue
        end

        start_time = times(j);
        changed_state = states(j);
        if isnan(state)
            previous_state = 1 - changed_state;
        else
            previous_state = state;
        end

        return_idx = find(states(j+1:end) == previous_state, 1, 'first');
        if isempty(return_idx)
            duration = 0;
            state = changed_state;
            j = j + 1;
            code = input_name;
        else
            return_idx = j + return_idx;
            duration = times(return_idx) - start_time;
            state = previous_state;
            j = return_idx + 1;

            if duration <= slack_time
                code = trigger_name;
                duration = 0;
            else
                code = input_name;
            end
        end

        out(end+1).time = start_time;
        out(end).code = code;
        out(end).duration = duration;
    end
end

% Convert to table
if isempty(out)
    out_table = table([], strings(0,1), [], ...
        'VariableNames', {'time','code','duration'});
else
    out_table = struct2table(out);
end

% Sort by time
out_table = sortrows(out_table, 'time');
end

