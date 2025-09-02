function measures = nt_compute_photometry_measures(snippets,measures,params)
% nt_compute_photometry_measures. Computes per event measures
%
%  measures = nt_compute_photometry_measures(snippets,measures,params)
%
%   Computes for measures.photometry.(event_type).(channel.channel).(type)
%        snippet_mean, snippet_std, mean, max, min
%
% 2025, Alexander

unique_events = measures.unique_events;
events = table([measures.markers.time]',string({measures.markers.marker}'),'VariableNames',{'time','event'});

mask_post = (measures.photometry_snippets_tbins>0);

for event_type = unique_events(:)'
    ind = find(events.event==event_type);
    for c = 1:length(measures.channels)
        channel = measures.channels(c);
        for i = 1:length(channel.lights)

            type = channel.lights(i).type;
            measures.photometry.(event_type).(channel.channel).(type).snippet_mean = mean(snippets.(channel.channel).(type)(ind,:),1);
            measures.photometry.(event_type).(channel.channel).(type).snippet_std = std(snippets.(channel.channel).(type)(ind,:),1);
            measures.photometry.(event_type).(channel.channel).(type).snippet_sem = sem(snippets.(channel.channel).(type)(ind,:),1);
            measures.photometry.(event_type).(channel.channel).(type).mean = mean(measures.photometry.(event_type).(channel.channel).(type).snippet_mean(mask_post));
            measures.photometry.(event_type).(channel.channel).(type).max = max(measures.photometry.(event_type).(channel.channel).(type).snippet_mean(mask_post));
            measures.photometry.(event_type).(channel.channel).(type).min = min(measures.photometry.(event_type).(channel.channel).(type).snippet_mean(mask_post));
        end % lights i
    end % channel c
end % event_type