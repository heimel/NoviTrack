function [events,triggers_received] = nt_load_laser_triggers(record,neurotar_data,params)
%nt_load_laser_triggers. Loads laser trigger log for record
%
% [events,triggers_received] = nt_load_laser_triggers(record,[neurotar_data],[params])
%
%   neurotar_data is only used to suggest the best matching trigger in case multiple
%   triggers were received.
%
%   events is array of structs
%     .code = code as occuring in laser log file 
%     .time = time relative to chosen received trigger and correct by
%             division by params.laser_time_multiplier
%     .duration = duration of event
%
% 2024, Alexander Heimel

if nargin<2 
    neurotar_data = [];
end
if nargin<3 || isempty(params)
    params = nt_default_parameters(record);
end

events = [];
triggers_received = {};

pth = nt_session_path(record,params);
filename = fullfile(pth,[record.sessionid '_laser_triggers.csv']);

if ~exist(filename,'file')
    logmsg(['No laser trigger file for record ' recordfilter(record)])
    return
end

lines = readlines(filename);

if isempty(lines)
    logmsg(['Empty laser trigger file for record ' recordfilter(record)])
    return    
end

start_time = [];
count = 1;

ind = find(contains(lines,'Received trigger'));
if isempty(ind)
    logmsg(['No trigger received in laser trigger log for record ' recordfilter(record)])
    return
end
received_lines = lines(ind);
event_lines = lines(setdiff(1:length(lines),ind));

if length(received_lines)>1
    logmsg(['Multiple triggers received in laser trigger log for record ' recordfilter(record)])
    logmsg('Loading neurotar data to suggest match.')
    if isempty(neurotar_data)
        neurotar_data = nt_load_neurotar_data(record);
    end
    ind = find(neurotar_data.TTL_outputs==1,1);
    ttl_time_on_neurotar = neurotar_data.SW_timestamp(ind);
end

for i = 1:length(received_lines)
    line = received_lines{i};
    ind = find(line==',');
    if isempty(ind)
            continue
    end
    if isempty(ind)
        logmsg(['Missing timestamp in line ' num2str(i) ' of ' filename]);
        continue
    end
    timestamp = line(1:(ind(2)-1));
    t = datetime(timestamp,'format','yyyy-MM-dd HH:mm:ss,SSS','TimeZone','Europe/Amsterdam');
    triggers_received{end+1} = datetime(t); %#ok<AGROW>
    
end % i
time_between = cellfun(@(x) seconds(time(between(ttl_time_on_neurotar,x))),triggers_received);

if isempty(triggers_received)
    logmsg(['Could not detect trigger time in record ' recordfilter(record)])
    return
end


if length(triggers_received)==1
    start_time = triggers_received{1};
else
    disp('Triggers received in laser log file:')
    for i = 1:length(triggers_received )
        fprintf('%3d: %s\n',i, string(triggers_received{i}) )
    end
    disp('Trigger time in neurotar log file:')
    fprintf('TTL: %s\n',ttl_time_on_neurotar);
    [d,i] = min(time_between);
    fprintf('Best match is trigger %d with %.2f s time difference.\n',i,d )
    question = ['Select trigger (Default=' num2str(i) ', select 0 to cancel):' ];
    result = input(question);
    if result==0 
        return
    end
    if isempty(result) 
        result = i;
    end
    if result<1 || result>length(triggers_received)
        logmsg('Invalid choice')
        return;
    end
    start_time = triggers_received{result};
end



for i = 1:length(event_lines)
    line = event_lines{i};
    ind = find(line==',');
    if isempty(ind)
        continue
    end
    if isempty(ind)
        logmsg(['Missing timestamp in line ' num2str(i) ' of ' filename]);
        continue
    end
    timestamp = line(1:(ind(2)-1));
    t = datetime(timestamp,'format','yyyy-MM-dd HH:mm:ss,SSS','TimeZone','Europe/Amsterdam');

    events(count).code = strtrim(line(ind(3)+1:ind(4)-1)); %#ok<AGROW>
    events(count).time = seconds(time(between(start_time,t,'Time'))) / params.laser_time_multiplier; %#ok<AGROW>
    events(count).duration =  str2double(strtrim(line(ind(4)+1:end))); %#ok<AGROW>
    count = count + 1;
end
