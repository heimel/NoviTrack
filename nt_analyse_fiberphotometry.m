function record = nt_analyse_fiberphotometry(record,verbose)
%nt_analyse_fiberphotometry. Analyse fiber photometry signal time locked to markers
%
%   RECORD = nt_analyse_fiberphotometry(RECORD,VERBOSE=true)
%
% 2025, Alexander Heimel

if nargin<2 || isempty(verbose)
    verbose = true;
end

measures = record.measures;

params = nt_default_parameters( record );

%% Load fiber photometry data

folder = fullfile(params.networkpathbase,record.project,'Data_collection',record.dataset,record.subject,record.sessionid);

d = dir(fullfile(folder,'Fluorescence-unaligned.csv'));
if isempty(d)
    d = dir(fullfile(folder,'20*'));
    if isempty(d)
        logmsg(['Cannot find fiber photometry data for ' recordfilter(record)]);
        return
    end
    folder = fullfile(folder,d.name);
end


fluorescence = readtable(fullfile(folder, "Fluorescence-unaligned.csv"));
lights = unique(fluorescence.Lights);
n_lights = length(lights);
channels = unique(setdiff(fluorescence.Properties.VariableNames,{'TimeStamp','Lights'}));
n_channels = length(channels);
fluorescence.TimeStamp = fluorescence.TimeStamp/1000; % change to s

events = readtable(fullfile(folder, "Events.csv"));
events.Name = categorical(events.Name);
events.TimeStamp = events.TimeStamp/1000; % change to s

triggers_fp = events.TimeStamp(events.Name == "Input1" & events.State==0);

if isempty(triggers_fp)
    logmsg('No triggers found on Input1')
    if ~isempty(events)
        logmsg('But there are triggers on other inputs')
    end
    return
end


% align fp time to marker time
fluorescence.time = nt_change_times(fluorescence.TimeStamp,triggers_fp,measures.trigger_times); 

%% Produce snippets


% the name changes is a leftover from an earlier function. here it
% indicates the marker

changes = table([measures.markers.time]',string({measures.markers.marker}'),'VariableNames',{'time','change'});
unique_changes = unique(changes.change);
measures.unique_changes = unique_changes;



measures.fp = [];
for i = 1:length(unique_changes)
    change = unique_changes(i);
    ind = find(changes.change==change);
    
    measures.fp.(change).n_trials = length(ind);
    t = cell(n_lights,1);
    f = cell(n_lights,n_channels);
    f_baseline = cell(n_lights,n_channels);
    for light = 1:n_lights
        for j = 1:length(ind) % events 
            event_time = changes.time(ind(j));
            ind_pre = ...
                fluorescence.TimeStamp>(event_time - params.nt_photometry_pretime) & ...
                fluorescence.TimeStamp<event_time & ...
                fluorescence.Lights==lights(light);

            ind_post = ...
                fluorescence.TimeStamp>=event_time  & ...
                fluorescence.TimeStamp<(event_time + params.nt_photometry_posttime) & ...
                fluorescence.Lights==lights(light);

            t{light} = [t{light}; fluorescence.TimeStamp(ind_pre | ind_post)-event_time];

            for c = 1:length(channels)
                f0 = median(fluorescence.(channels{c})(ind_pre));

                f{light,c} = [f{light,c}; (fluorescence.(channels{c})(ind_pre | ind_post) - f0)/f0];
                f_baseline{light,c} = [f_baseline{light,c}; (fluorescence.(channels{c})(ind_pre) - f0)/f0];
            end % c
        end
        [t{light},ind_t] = sort(t{light});
        for c = 1:n_channels
            f{light,c} = f{light,c}(ind_t);
            m = mean(f_baseline{light,c});
            s = std(f_baseline{light,c});
            z = (f{light,c}-m)/s;

            [dfof{light,c},dfof_t{light,c}] = slidingwindowfunc(t{light},f{light,c},...
                -params.nt_photometry_pretime,0.01,params.nt_photometry_posttime,0.03,[],NaN);

            zscore{light,c} = slidingwindowfunc(t{light},z,...
                -params.nt_photometry_pretime,0.01,params.nt_photometry_posttime,0.03,[],NaN);
        end % channel
    end % light 

    measures.fp.t = dfof_t{1,1}; % perhaps we should keep t light dependent

    ind_post = measures.fp.t > 0;
    ind_pre = measures.fp.t < 0;

    for c = 1:n_channels
        measures.fp.(change).(channels{c}).dfof = dfof{2,c};
        % measures.fp.(change).max_dfof = max(measures.fp.(change).dfof(ind_post));
        % measures.fp.(change).mean_dfof = mean(measures.fp.(change).dfof(ind_post));
        % measures.fp.(change).range_dfof = max(measures.fp.(change).dfof(ind_post))-min(measures.fp.(change).dfof(ind_post));

        measures.fp.(change).(channels{c}).zscore = zscore{2,c};
        % measures.fp.(change).max_zscore = max(measures.fp.(change).zscore(ind_post));
        % measures.fp.(change).mean_zscore = mean(measures.fp.(change).zscore(ind_post));
        % measures.fp.(change).range_zscore = max(measures.fp.(change).zscore(ind_post))-min(measures.fp.(change).zscore(ind_post));

        measures.fp.(change).(channels{c}).dfof_isos = dfof{1,c};
        % measures.fp.(change).max_dfof_isos = max(measures.fp.(change).dfof_isos(ind_post));
        % measures.fp.(change).mean_dfof_isos = mean(measures.fp.(change).dfof_isos(ind_post));
        % measures.fp.(change).range_dfof_isos = max(measures.fp.(change).dfof_isos(ind_post))-min(measures.fp.(change).dfof_isos(ind_post));

        measures.fp.(change).(channels{c}).zscore_isos = zscore{1,c};
        % measures.fp.(change).max_zscore_isos = max(measures.fp.(change).zscore_isos(ind_post));
        % measures.fp.(change).mean_zscore_isos = mean(measures.fp.(change).zscore_isos(ind_post));
        % measures.fp.(change).range_zscore_isos = max(measures.fp.(change).zscore_isos(ind_post))-min(measures.fp.(change).zscore_isos(ind_post));
    end % channel c
end % change i





%% Clean up

record.measures = measures;