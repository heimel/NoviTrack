function [photometry,measures] = nt_load_photometry(record,params)
% nt_load_photometry. Load photometry data into photometry struct
%
%  [photometry,measures] = nt_load_photometry(record,[PARAMS])
%
%  photometry.(channel).(type) = struct
%   'time' [n_samples x 1] = time stamps in master time
% 	'signal' [n_samples x 1] = signal
%
% measures will be updated with 
%
% measures.channels = struct array
% 	'channel' = char() name, e.g. 'Channel1'
% 	'location' = char() location, 'lights'
% 	'lights' = struct array
% 		'wavelength' = int wavelength, e.g. 410
% 		'type' = char() lowercase name, e.g. 'gda3m', 'isosbestic'
%   'fit_isos' = parameters for isosbestic correction
%   'sampling_rate' = double, sampling rate in Hz.
%
% measures.period_of_interest = [1x2] with start and stop time of period of interest in master time
%
%  See nt_data_structures.md for more information.
%
% 2025, Alexander Heimel

if nargin<2 || isempty(params)
    params = nt_default_parameters( record );
end

measures = record.measures;
photometry = [];

measures.period_of_interest = [];
if isfield(measures,'channels')
    measures = rmfield(measures,'channels');
end

[folder,found] = nt_photometry_folder(record);
if ~found
    return
end

fluorescence = readtable(fullfile(folder, "Fluorescence-unaligned.csv"));

wavelengths = unique(fluorescence.Lights);

% get matching of channels to fibers
result = parse_channels(record.comment);

channel_names = unique(setdiff(fluorescence.Properties.VariableNames,{'TimeStamp','Lights'}));

if isempty(result)
    logmsg('No channels specified in comment. Assuming channelX = fiberX.')
    for i=1:length(channel_names)
        channel_name = channel_names{i};
        result.(channel_name) = ['fiber' channel_names{i}(8:end)];
    end
end

for c = 1:length(channel_names)
    channel_name = channel_names{c};
    fiber = result.(channel_name);
    if isfield(measures,'fiber_info') && isfield(measures.fiber_info,fiber)
        fiber_info = measures.fiber_info.(fiber);
    else
        fiber_info.hemisphere = '';
        fiber_info.location = '';
        fiber_info.green_sensor = 'green_sensor';
        fiber_info.red_sensor = 'red_sensor';
    end

    for i = 1:length(wavelengths)
        lights(i) = struct('wavelength',wavelengths(i),'type',''); %#ok<AGROW>
        switch wavelengths(i)
            case 410
                lights(i).type = 'isosbestic'; %#ok<AGROW>
            case 470 
                lights(i).type = 'green'; %#ok<AGROW> 
            case 560
                lights(i).type = 'red'; %#ok<AGROW> 
            otherwise
                lights(i).type = 'unknown';
        end
    end
    measures.channels(c) = struct('channel',channel_name,...
        'hemisphere',fiber_info.hemisphere,...
        'location',fiber_info.location,...
        'green_sensor',fiber_info.green_sensor,...
        'red_sensor',fiber_info.red_sensor,...
        'lights',lights,...
        'fit_isos',[],...
        'sample_rate',[]);
end % c

% Change time from ms to s
fluorescence.TimeStamp = fluorescence.TimeStamp/1000; 

% Align fp time to marker time
triggers_fp = nt_load_rwd_triggers(record);
if isempty(triggers_fp)
    logmsg('No recorded RWD triggers. Assuming 0.');
    triggers_fp = 0;
end

if ~isfield(measures,'trigger_times') 
    logmsg('TEMPORARY FOR MDJ DATA: EQUALIZING TRIGGERS')
    measures.trigger_times = triggers_fp;
end

fluorescence.time = nt_change_times(fluorescence.TimeStamp,triggers_fp,measures.trigger_times);

if ~isfield(measures,'markers') || isempty(measures.markers)
    record.measures = measures;
    record = nt_import_markers(record,'RWD log');
    measures = record.measures;
end



% Determine period of interest
measures.period_of_interest = [-Inf Inf];
if isfield(measures,'markers') && ~isempty(measures.markers) 
    % if there are markers
    measures.period_of_interest(1) = max(fluorescence.time(1),min([measures.markers.time]) - params.nt_photometry_pretime * 2);
    measures.period_of_interest(2) = min(fluorescence.time(end),max([measures.markers.time]) + params.nt_photometry_posttime * 2);
else
    % otherwise remove first and last 5% of the data
    duration = fluorescence.time(end) - fluorescence.time(1);
    measures.period_of_interest(1) = fluorescence.time(1) + duration * 0.05;
    measures.period_of_interest(2) = fluorescence.time(end) - duration * 0.05;
end


% Convert to photometry structure
for c = 1:length(measures.channels)
    channel = measures.channels(c);
    for i = 1:length(channel.lights)
            type = channel.lights(i).type;
            photometry.(channel.channel).(type).time = fluorescence.time(fluorescence.Lights==channel.lights(i).wavelength);
            photometry.(channel.channel).(type).signal = fluorescence.(channel.channel)(fluorescence.Lights==channel.lights(i).wavelength);
    end
    dt = median(diff(photometry.(channel.channel).(type).time));
    measures.channels(c).sample_rate = 1/dt;
end % c



end





function result = parse_channels(comment)
%PARSE_CHANNELS Parse channel mappings from a comment string.

pattern = 'channel(\d+)\s*=\s*([^,]+)';
tokens = regexp(comment, pattern, 'tokens', 'ignorecase');

result = struct();

for i = 1:numel(tokens)
    key = sprintf('Channel%s', strtrim(tokens{i}{1}));
    value = lower(strtrim(tokens{i}{2})); % fiberX made lower caser
    if value(end)=='.'
        value = value(1:end-1);
    end

    result.(key) = value;
end
end

