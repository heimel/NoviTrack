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

if isempty(snippets)
    measures.event = [];
    return
end

events = table([measures.markers.time]',string({measures.markers.marker}'),'VariableNames',{'time','event'});
unique_events = unique(events.event);

mask_post = (measures.snippets_tbins>0);
flds = fields(snippets.data);

for event_type = unique_events(:)'
    ind = find(events.event==event_type);
    for i = 1:length(flds)
        field = flds{i};
        snippet_mean = mean(snippets.data.(field)(ind,:),1);
        measures.event.(event_type).(field).snippet_mean = snippet_mean;
        measures.event.(event_type).(field).snippet_first = snippets.data.(field)(ind(1),:);
        measures.event.(event_type).(field).snippet_std = std(snippets.data.(field)(ind,:),1); % over snippets
        measures.event.(event_type).(field).snippet_sem = sem(snippets.data.(field)(ind,:),1);  % over snippets
        measures.event.(event_type).(field).mean = mean(snippet_mean(mask_post));
        measures.event.(event_type).(field).max = max(snippet_mean(mask_post));
        measures.event.(event_type).(field).min = min(snippet_mean(mask_post));
        measures.event.(event_type).(field).n = length(ind); % assume measured for all events
        measures.event.(event_type).(field).event_mean = mean(snippets.data.(field)(ind,:),2); % mean response over time
    end % field
end % event_type

