function snippets = nt_make_motion_snippets(nt_data,measures,snippets,params)
% nt_make_motion_snippets. Cut out snippets around marker times from motion data
%
%  SNIPPETS = nt_make_motion_snippets(NT_DATA,MEASURES,[SNIPPETS],PARAMS)
%
%  SNIPPETS.data.(channel_type) = n_markers x n_bins_per_snippet
%  SNIPPETS.baseline_std.(channel_type) = n_markers x 1
%
%  uses measures.snippets_tbins = t_bins and measures.markers
%
%  See nt_data_structures.md for more information.
%
% 2025, Alexander Heimel

if nargin<3 || isempty(snippets)
    snippets = [];
end

if isempty(measures.markers) || isempty(nt_data)
    return
end

events = table([measures.markers.time]',string({measures.markers.marker}'),'VariableNames',{'time','event'});
n_events = height(events);


t_bins = measures.snippets_tbins;

observables = ["Speed","Angular_velocity"];

measures.correlation = [];
for observable = observables(:)'
    if all(isnan(nt_data.(observable)))
        continue
    end
    for j = 1:n_events
        event_time = events.time(j);
        time = nt_data.Time;
        mask = time> (event_time - params.nt_photometry_pretime - params.nt_photometry_bin_width) & ...
            time < (event_time + params.nt_photometry_posttime + params.nt_photometry_bin_width);
        if any(mask)
            snippet = interp1(time(mask),nt_data.(observable)(mask),event_time + t_bins,[],'extrap');
            snippets.data.(observable)(j,:) = snippet;
            snippets.unit.(observable) = 'a.u.';
        else
            logmsg(['No samples for event at ' num2str(event_time)])
            snippets.data.(observable)(j,:) = NaN(size(t_bins));
            snippets.unit.(observable) = 'a.u.';

        end

    end % events j
end % variable v