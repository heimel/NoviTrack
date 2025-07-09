function [triggers,events] = nt_load_rwd_triggers(record)
%nt_load_rwd_triggers. Loads events file from RWD fiber photometer
%
%  [TRIGGERS,EVENTS] = nt_load_rwd_triggers(RECORD)
%        TRIGGERS in seconds is on RWD clock
%        EVENTS is table with fields: time, code, duration
%
% 2025, Alexander Heimel

params = nt_default_parameters( record );

folder = fullfile(params.networkpathbase,record.project,'Data_collection',record.dataset,record.subject,record.sessionid);

triggers = [];
events = [];

d = dir(fullfile(folder,'Fluorescence-unaligned.csv'));
if isempty(d)
    d = dir(fullfile(folder,'20*'));
    if isempty(d)
        logmsg(['Cannot find fiber photometry data for ' recordfilter(record)]);
        return
    end
    folder = fullfile(folder,d.name);
end

events = readtable(fullfile(folder, "Events.csv"));
events.Name = categorical(events.Name);
events.TimeStamp = events.TimeStamp/1000; % change to s

triggers = events.TimeStamp(events.Name == "Input1" & events.State==0);

if isempty(triggers)
    logmsg('No triggers found on Input1')
    if ~isempty(events)
        logmsg('But there are triggers on other inputs')
    end
    return
end


prev_state = params.rwd_initial_input_state;
events = convert_event_rwd(events, prev_state);



end

function out_table = convert_event_rwd(event_rwd, prev_state)
    input_names = {"Input1", "Input2","Input3","Input4","Input5"};
    trigger_names = {"Trigger1","Trigger2","Trigger3","Trigger4","Trigger5"};
    
    % Preallocate output
    out = struct('time', {}, 'code', {}, 'duration', {});
    
    for i = 1:2
        input_name = input_names{i};
        trigger_name = trigger_names{i};
        state = prev_state(i);
        
        % Extract events for this input
        idx = (event_rwd.Name==input_name );
        times = event_rwd.TimeStamp(idx);
        states = event_rwd.State(idx);
        
        % Append the starting state
        %full_state = [state; states];
        %full_time = [NaN; times];  % no timestamp for prev_state
        
        % Loop over transitions
        for j = 1:length(states)
            if states(j) ~= state

                out(end+1).time = times(j);
                out(end).code = trigger_name;

                % Duration is time to next event in this input
                if j < length(times)
                    out(end).duration = times(j+1) - times(j);
                else
                    out(end).duration = 0;
                end
            end
        end
    end
    
    % Convert to table
    out_table = struct2table(out);
    
    % Sort by time
    out_table = sortrows(out_table, 'time');
end

