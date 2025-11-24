function measures = nt_compute_event_measures(snippets,measures,params)
% nt_compute_event_measures. Computes per event measures
%
%  MEASURES = nt_compute_events_measures(SNIPPETS,MEASURES,PARAMS)
%
%   Computes for MEASURES.event.(event_type).(field)
%        snippet_mean, snippet_std, mean, max, min, event_mean
%   from SNIPPETS.data
%
%  See nt_data_structures.md for more information.
%
% 2025, Alexander

%% Compute measures for behavioral responses to stimuli
motifs = params.markers(find([params.markers.behavior]));
motif_list = [motifs.marker]; 
n_motifs = length(motifs);
events = measures.events;
unique_events = unique(events.event);
logmsg('WORKING HERE ON GETTING STIMULUS RESPONSES')

behaviors = get_behaviors(events,motif_list);

for event_type = unique_events(:)'
    event_type_char= char(event_type);
    if ~ismember(event_type_char(1),params.nt_stim_markers)
        continue
    end
    event_type
    ind_stim = find(events.event==event_type);

    for i = 1:n_motifs 
        motif = motif_list(i);
        latency = [];
        duration = 0;
        response = zeros(length(ind_stim),1);
        for j = 1:length(ind_stim)
            stim_start = events.time(ind_stim(j));
            stim_stop = events.time(find(events.time>stim_start & events.event == string([ params.nt_stop_marker event_type_char(2)]),1));

            ind = find(behaviors.time>stim_start & behaviors.time<stim_stop & behaviors.event == motif);
            if isempty(ind)
                continue
            else
                response(j) = 1;
            end

            latency(end+1) = behaviors.time(ind(1)) - stim_start;

            for k = 1:length(ind)

                if ind(k)==height(behaviors)
                    duration = duration + measures.max_time - behaviors.time(ind(k));
                else
                    duration = duration + behaviors.time(ind(k)+1) - behaviors.time(ind(k)); 
                end
            end % k
        end % j 
        measures.behavior.(event_type).(motif).n = length(latency); % all response, multiple per stim possible
        measures.behavior.(event_type).(motif).response = sum(response); % response, max one per stim.
        measures.behavior.(event_type).(motif).response_fraction = sum(response)/length(ind_stim); % fraction of stimuli with a response
        measures.behavior.(event_type).(motif).latency = mean(latency,'omitnan');
        measures.behavior.(event_type).(motif).duration = duration/length(ind_stim);
    end % motif i

end % event_type


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
        measures.event.(event_type).(field).snippet_sem = sem(snippets.data.(field)(ind,:),1);  % over snippets
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

