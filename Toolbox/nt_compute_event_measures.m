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
behaviors = get_behaviors(events,motif_list);

for event_type = unique_events(:)'
    event_type_char= char(event_type);
    if ~ismember(event_type_char(1),params.nt_stim_markers)
        continue % if not a stimulus
    end
    ind_stim = find(events.event==event_type);

    for i = 1:n_motifs
        motif = motif_list(i);
        latency = [];
        duration = 0;
        response = zeros(length(ind_stim),1);
        for j = 1:length(ind_stim)
            stim_start = events.time(ind_stim(j));
            ind_stop = find(events.time>stim_start & events.event == string([ params.nt_stop_marker event_type_char(2)]),1);
            if isempty(ind_stop)
                % stim_stop = inf; % not until next stimulus, but until end of time
                logmsg(['Stop marker missing for event type ' event_type_char '. Temporarily taking to end of video, but should be added.'])
                stim_stop = measures.video_info(2).Duration;
            else
                stim_stop = events.time(ind_stop);
            end
            total_stim_time = stim_stop - stim_start; % to define the start and end of one stimuli
            ind = find(behaviors.time>stim_start & behaviors.time<stim_stop & behaviors.event == motif);
            count = length(ind);
            if isempty(ind)
                continue
            else
                response(j) = 1;
            end
            latency(end+1) = behaviors.time(ind(1)) - stim_start; %#ok<AGROW>
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
        measures.behavior.(event_type).(motif).duration_percent = duration/total_stim_time*100; % calculate the duration percent
        measures.behavior.(event_type).(motif).duration_fraction = duration/total_stim_time; % behavior duration as fractioin of total time
        % duration_fraction can be over 100%, as the duration of the
        % behavior is counted until the end of the behavior, not until
        % the end of the stimulus
        measures.behavior.(event_type).(motif).rate = sum(response)/total_stim_time; % calculate the response rate

        if measures.behavior.(event_type).(motif).duration_fraction==0 && measures.behavior.(event_type).(motif).duration~=0
            keyboard
        end

    end % motif i

end % event_type


%% compute motif statistics for non-stimulus linked behavior
for i = 1:n_motifs
    motif = motif_list(i);
    duration = 0;
    ind = find(behaviors.event == motif);
    count = length(ind);
    if isempty(ind)
        continue
    end
    for k = 1:length(ind)
        if ind(k) == height(behaviors)
            duration = duration + measures.max_time - behaviors.time(ind(k));
        else
            duration = duration + behaviors.time(ind(k)+1) - behaviors.time(ind(k));
        end % end if
    end  % end k
    measures.behavior.spontaneous.(motif).duration_total = duration;
    measures.behavior.spontaneous.(motif).duration_average = duration/count;
    measures.behavior.spontaneous.(motif).count = count;
end % end motif i


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

