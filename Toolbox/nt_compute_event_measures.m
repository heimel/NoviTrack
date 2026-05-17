function measures = nt_compute_event_measures(snippets,measures,params)
% nt_compute_event_measures. Computes per event measures
%
%  MEASURES = nt_compute_events_measures(SNIPPETS,MEASURES,PARAMS)
%
%   Computes for MEASURES.event.(event_type).(field)
%        snippet_mean, snippet_std, mean, max, min, event_mean
%   from SNIPPETS.data
%
%   and for MEASURES.behavior.(EVENT_TYPE).(MOTIF).(FIELD)
%   where MOTIF is a behavior and event_type is a type of event or 'session'
%   for events, the measures are calculated for the period the stimulus is present
%   FIELD is
%       n_occurences_per_stimulus: # of occurrences per stimulus, multiple per stimulus possible.
%       n_responses_per_stimulus: # of occurrences per stimulus, with max. one per stim.
%       shortest_latency: shortest latency of the first response 
%       duration_per_stimulus: average duration of the response per stimulus;
%           duration can be longer than the stimulus, as it is counted
%           until the end of the behavior, not of the stimulus
%       duration_fraction: fraction of average duration of the stimulus duration
%       duration_per_occurence: total duration / # of occurrences
%       interval: mean time between start of occurrences 
%       rate: # of occurrences / total stimulus time
%   for EVENT_TYPE is 'session', FIELD is
%       n_occurrences_per_session: # occurrences per session
%       duration_per_session: total duration per session
%       duration_per_occurrence: total duration / # of occurrence
%       interval: mean time between start of occurrences 
%       duration_fraction:  duration / marked_period;
%       rate: # of occurrences / marked_period; 
%       duration_fraction_of_movie: duration / movie_duration; 
%       rate_in_movie: count / movie_duration; 
%      
%
%  See nt_data_structures.md for more information.
%
% 2025-2026, Alexander

%% Compute measures for behavioral responses to stimuli
motifs = params.markers(find([params.markers.behavior]));
motif_list = {motifs.marker};

% temporarily added for looming analysisn (where shelter is object 1)
motif_list = {motif_list{:},'a1','v1'};


n_motifs = length(motif_list);
if isempty(measures)
    return
end

events = nt_get_events(measures,params);
if isempty(events)
    measures.event = [];
    return
end
unique_events = unique(events.event);
behaviors = get_behaviors(events,motif_list);

for event_type = unique_events(:)'
    event_type_char= char(event_type);
    if ~ismember(event_type_char(1),params.nt_stim_markers)
        continue % if not a stimulus
    end
    ind_stim = find(events.event==event_type);
    n_stimuli = length(ind_stim);
    for i = 1:n_motifs % behaviors
        motif = motif_list{i};
        shortest_latency = inf; % s
        total_duration = 0; % s
        n_occurrences = 0;
        n_responses = 0;
        total_stim_duration = 0; % s
        intervals = [];
        for j = 1:n_stimuli % stimuli
            stim_start = events.time(ind_stim(j));
            ind_stop = find(events.time>stim_start & events.event == string([ params.nt_stop_marker event_type_char(2)]),1);
            if isempty(ind_stop)
                logmsg(['Stop marker missing for event type ' event_type_char '. Temporarily taking to end of video, but should be added.'])
                stim_stop = measures.max_time;
            else
                stim_stop = events.time(ind_stop);
            end
            stim_duration = stim_stop - stim_start; % to define the start and end of one stimuli
            total_stim_duration = total_stim_duration + stim_duration;
 
            ind = find(behaviors.time>stim_start & behaviors.time<stim_stop & behaviors.event == motif);
            if isempty(ind) % no response
                continue
            end
            n_responses = n_responses + 1;
            n_occurrences = n_occurrences + length(ind);

            latency = behaviors.time(ind(1)) - stim_start; 
            if latency < shortest_latency
                shortest_latency = latency;
            end

            intervals = [intervals; diff(behaviors.time(ind))];

            for k = 1:length(ind)
                if ind(k)==height(behaviors)
                    duration =  stim_stop - behaviors.time(ind(k));
                    logmsg(['No end for ' behaviors.event(ind(k)) '. Taking end of stimulus'])
                else
                    duration =  behaviors.time(ind(k)+1) - behaviors.time(ind(k));
                end
                total_duration = total_duration + duration;
            end % response k
        end % stimulus j

        res.n_occurrences_per_stimulus = n_occurrences / n_stimuli;
        res.n_responses_per_stimulus = n_responses / n_stimuli; 
        res.shortest_latency = shortest_latency;
        res.duration_per_stimulus = total_duration / n_stimuli;
        res.duration_fraction = total_duration / total_stim_duration;
        res.duration_per_occurrence = total_duration / n_occurrences;
        res.interval = mean(intervals);
        res.rate = n_occurrences / total_stim_duration;

        measures.behavior.(event_type).(motif) = res;
    end % motif i
end % event_type


%% compute motif statistics for behavior during full session
for i = 1:n_motifs
    motif = motif_list{i};
    total_duration = 0; % s
    ind = find(behaviors.event == motif);
    n_occurrences = length(ind);
    for k = 1:length(ind)
        if ind(k) == height(behaviors)
            duration = measures.max_time - behaviors.time(ind(k));
            logmsg(['No end for ' behaviors.event(ind(k))])
        else
            duration = behaviors.time(ind(k)+1) - behaviors.time(ind(k));
        end
        total_duration = total_duration + duration;
    end % behavior k

    marked_period = events.time(end) - events.time(1);
    movie_duration = measures.max_time - measures.min_time;

    res.n_occurrences_per_session = n_occurrences;
    res.duration_per_session = total_duration;
    if n_occurrences > 0 
        res.duration_per_occurrence = total_duration / n_occurrences;
    else
        res.duration_per_occurrence = NaN;
    end
    res.interval = mean(diff(events.time(ind)));
    res.duration_fraction = total_duration / marked_period;
    res.rate = n_occurrences / marked_period; 
    res.duration_fraction_of_movie = total_duration / movie_duration; 
    res.rate_in_movie = n_occurrences / movie_duration;

    measures.behavior.session.(motif) = res;
end % motif i


%% Compute results from snippets 
if isempty(snippets)
    measures.event = [];
    return
end

mask_post = (measures.snippets_tbins>0);
flds = fields(snippets.data);

for event_type = unique_events(:)'
    ind = find(events.event==event_type);
    for i = 1:length(flds)
        field = flds{i};
        snippet_mean = mean(snippets.data.(field)(ind,:),1,'omitnan');
        measures.event.(event_type).(field).snippet_mean = snippet_mean;
        measures.event.(event_type).(field).snippet_first = snippets.data.(field)(ind(1),:);
        measures.event.(event_type).(field).snippet_std = std(snippets.data.(field)(ind,:),1,'omitnan'); % over snippets
        measures.event.(event_type).(field).snippet_sem = ivt_sem(snippets.data.(field)(ind,:),1);  % over snippets
        measures.event.(event_type).(field).mean = mean(snippet_mean(mask_post));
        measures.event.(event_type).(field).max = max(snippet_mean(mask_post));
        measures.event.(event_type).(field).min = min(snippet_mean(mask_post));
        measures.event.(event_type).(field).n = length(ind); % assume measured for all events
        measures.event.(event_type).(field).event_mean = mean(snippets.data.(field)(ind,:),2); % mean response over time
        measures.event.(event_type).(field).unit = snippets.unit.(field);
    end % field
end % event_type

%
function behaviors = get_behaviors(events,motif_list)
behaviors = events;
i = 1;
while i<=height(behaviors)
    marker = char(behaviors.event(i));
    marker = marker(1);
    if ~ismember(marker,motif_list)
        behaviors(i,:) = [];
    else
        i = i + 1;
    end
end

