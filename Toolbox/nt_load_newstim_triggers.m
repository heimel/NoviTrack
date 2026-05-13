function [triggers,events] = nt_load_newstim_triggers(record,fields2add)
%nt_load_newstim_triggers. Loads triggers and creates events from NewStim
%folders
%
%  [TRIGGERS,EVENTS] = nt_load_newstim_triggers(RECORD,FIELDS2ADD = {})
%        FIELDS2ADD is a cell list with parameters to add to EVENTS.
%        TRIGGERS in seconds from stimulus computer clock (from stims.mat)
%        EVENTS is table with fields: time, code, duration
%               time is stimulus computer clock
%
% 2025-2026, Alexander Heimel

if nargin<2 || isempty(fields2add)
    fields2add = {};
end

triggers = [];
events = [];


params = nt_load_parameters(record);
session_path = nt_session_path(record,params);
d = dir(fullfile(session_path,'t00*'));
d = d([d.isdir]);
[~,ind] = sort([d.datenum]);
d = d(ind);

if isempty(d)
    logmsg('No NewStim folders')
    return
end

stims = cell(length(d),1);
count = 1;
time = [];
code = [];
dur = [];
unique_scripts = [];
for i = 1:length(d)
    filename = fullfile(session_path,d(i).name,'stims.mat');
    if ~exist(filename,'file')
        continue
    end
    stims{count} = load(filename);
    if ~isa(stims{count}.saveScript,'stimscript')
        logmsg('Not recognizing stimulus script. Make sure to add NewStim3 to the MATLAB path and run NewStimInit.');
        break
    end

    triggers(count,1) = stims{count}.start; %#ok<AGROW>
    time(count,1) =  stims{count}.start; %#ok<AGROW>
    dur(count,1) = duration(stims{count}.saveScript); %#ok<AGROW>
    new_stimulus = true;
    for j = 1:length(unique_scripts)
        if stims{count}.saveScript == unique_scripts{j}
            script_id = j;
            new_stimulus = false;
            break;
        end
    end
    if new_stimulus
        unique_scripts{end+1} = stims{count}.saveScript; %#ok<AGROW>
        script_id = length(unique_scripts);
    end
    code{count,1} = "h" + num2str(script_id); %#ok<AGROW>
    count = count + 1;
end
code = string(code);

events = table(time,code,dur,'VariableNames',{'time','code','duration'});

% add columns with parameters in which the stimuli differ
ss = cellfun(@(ss) getparameters(ss),unique_scripts);
fields = find_differing_fields(ss);
fields = unique({fields{:},fields2add{:}});
for f = 1:length(fields)
    field = fields{f};
    val = cellfun( @(c) getparameters(unique_scripts{str2double(c(2:end))}).(field), code);
    events.(field) = val;
end % f

if ~all(diff(triggers)>0)
    logmsg(['Stimulus times are not all in increasing order. Resorting, but check results for ' recordfilter(record)]);
    triggers = sort(triggers);
    events = sortrows(events,'time');
end
