function snippets = nt_make_photometry_snippets(photometry,measures,params)
% nt_make_photometry_snippets. Cut out snippets around marker times from photometry data
%
%  SNIPPETS = nt_make_photometry_snippets(PHOTOMETRY,MEASURES,PARAMS)
%
%  Snippets around signal around marker time, z-scored by pre-marker baseline
%  subtraction and normalized by common standard deviation of baseline
%  signal.
%
%  SNIPPETS.data.(channel_type) = n_markers x n_bins_per_snippet
%  SNIPPETS.baseline_std.(channel_type) = n_markers x 1
%
%  uses measures.snippets_tbins = t_bins and measures.markers
%
% 2025, Alexander Heimel

snippets = [];

if ~isfield(measures,'markers') || isempty(measures.markers)
    return
end

%events = table([measures.markers.time]',string({measures.markers.marker}'),'VariableNames',{'time','event'});
events = measures.events;
n_events = height(events);

t_bins = measures.snippets_tbins;
n_bins_per_snippet = length(t_bins);

mask_pre = (t_bins<0);

for c = 1:length(measures.channels)
    channel = measures.channels(c);
    for i = 1:length(channel.lights)
        type = channel.lights(i).type;
        field = [channel.channel '_' type];
        snippets.data.(field) = NaN(n_events,n_bins_per_snippet);
        snippets.unit.(field) = 'raw';
        for j = 1:n_events
            event_time = events.time(j);
            time = photometry.(channel.channel).(type).time;
            mask = time> (event_time - params.nt_pretime - params.nt_photometry_bin_width) & ...
                time < (event_time + params.nt_posttime + params.nt_photometry_bin_width);
            % interpolate at bin times;

            if sum(mask)<3
                logmsg(['No photometry data points for event at ' num2str(event_time,2) ' s.'])
                snippet = NaN(size(t_bins));
            else
                snippet = interp1(time(mask),photometry.(channel.channel).(type).signal(mask),event_time + t_bins,[],'extrap');
            end

            snippets.data.(field)(j,:) = snippet;
            if params.nt_photometry_subtract_baseline
                snippets.data.(field)(j,:) = snippets.data.(field)(j,:) - mean(snippet(mask_pre),'omitnan');
            end
        end % events j
        snippets.baseline_std.(field) = median(std(snippets.data.(field)(:,mask_pre),[],2,'omitnan'),'omitnan');
        if params.nt_photometry_zscoring
            snippets.data.(field) = snippets.data.(field)/snippets.baseline_std.(field);
            snippets.unit.(field) = 'zscore';
        end
    end % lights i
end % c 

end

