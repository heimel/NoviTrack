function [snippets,measures] = nt_make_photometry_snippets(photometry,measures,params)
% nt_make_photometry_snippets. Cut out snippets around marker times from photometry data
%
%  Snippets around signal around marker time, z-scored by pre-marker baseline
%  subtraction and normalized by common standard deviation of baseline
%  signal.
%
%  snippets.(channel.channel).(type) = n_markers x n_bins_per_snippet
%
%  measures.snippets_tbins = t_bins, centers of time bins relative to
%    marker time.
%  measures.unique_events = cell list of unique markers, e.g. {'h1','t1'}
%
% 2025, Alexander Heimel

events = table([measures.markers.time]',string({measures.markers.marker}'),'VariableNames',{'time','event'});
n_events = height(events);
unique_events = unique(events.event);
measures.unique_events = unique_events;

t_bins = (-params.nt_photometry_pretime + params.nt_photometry_bin_width/2):params.nt_photometry_bin_width:(params.nt_photometry_posttime-params.nt_photometry_bin_width/2);
n_bins_per_snippet = length(t_bins);

mask_pre = (t_bins<0);

for c = 1:length(measures.channels)
    channel = measures.channels(c);
    for i = 1:length(channel.lights)
        type = channel.lights(i).type;
        snippets.(channel.channel).(type) = NaN(n_events,n_bins_per_snippet);
        for j = 1:n_events
            event_time = events.time(j);
            time = photometry.(channel.channel).(type).time;
            mask = time> (event_time - params.nt_photometry_pretime - params.nt_photometry_bin_width) & ...
                time < (event_time + params.nt_photometry_posttime + params.nt_photometry_bin_width);
            % interpolate at bin times;
            snippet = interp1(time(mask),photometry.(channel.channel).(type).signal(mask),event_time + t_bins);
            snippets.(channel.channel).(type)(j,:) = snippet - mean(snippet(mask_pre));
        end % events j
        baseline_std.(channel.channel).(type) = median(std(snippets.(channel.channel).(type)(:,mask_pre),[],2));
        % z-score
        snippets.(channel.channel).(type) = snippets.(channel.channel).(type)/baseline_std.(channel.channel).(type); 
    end % lights i
end % c 

measures.photometry_snippets_tbins = t_bins;
measures.photometry_baseline_std = baseline_std;
end

%%

% measures.fp = [];
% for i = 1:length(unique_events)
%     event = unique_events(i);
%     ind = find(events.event==event);
%     n_events = length(ind);
%     measures.fp.(event).n_events = n_events;
% 
%     dfof = cell(n_lights,n_channels);
%     dfof_t = cell(n_lights,n_channels);
% 
%     for c = 1:n_channels
%         channel = channels{c};
% 
%         t = cell(n_lights,1);
%         f = cell(n_lights);
%         f_baseline = cell(n_lights);
% 
%         fp.(event).(channel).peristimulus = zeros(n_lights,n_events,n_bins_per_event);
% 
%         for light = 1:n_lights
%             for j = 1:n_events
%                 event_time = events.time(ind(j));
%                 mask_pre = ...
%                     fluorescence.time>(event_time - params.nt_photometry_pretime) & ...
%                     fluorescence.time<event_time & ...
%                     fluorescence.Lights==lights(light);
% 
%                 mask_post = ...
%                     fluorescence.time>=event_time  & ...
%                     fluorescence.time<(event_time + params.nt_photometry_posttime) & ...
%                     fluorescence.Lights==lights(light);
% 
%                  mask_all = mask_pre | mask_post;
% 
%                 % vq = interp1(x,v,xq)
%                 fp.(event).(channel).peristimulus(light,j,:) = ...
%                     interp1( fluorescence.time(mask_all)-event_time,...
%                     fluorescence.(channel)(mask_all),fp.t_bins);
% 
%                 t{light} = [t{light}; fluorescence.time(mask_all)-event_time];
% 
%                 f0 = mean(fluorescence.(channel)(mask_pre));
% 
%                 f{light} = [f{light}; (fluorescence.(channel)(mask_all) - f0)/f0];
%                 f_baseline{light} = [f_baseline{light}; (fluorescence.(channel)(mask_pre) - f0)/f0]; % used for z-scoring
%             end % event j
% 
% 
%             [t{light},ind_t] = sort(t{light});
%             f{light} = f{light}(ind_t);
% 
%             window = max(median(diff(t{light})),0.1);
% 
%             [dfof{light,c},dfof_t{light,c}] = slidingwindowfunc(t{light},f{light},...
%                 -params.nt_photometry_pretime,params.nt_photometry_window_width,params.nt_photometry_posttime,window,[],NaN);
% 
%             m = mean(f_baseline{light});
%             s = std(f_baseline{light});
%             z = (f{light}-m)/s;
% 
%             zscore{light,c} = slidingwindowfunc(t{light},z,...
%                 -params.nt_photometry_pretime,params.nt_photometry_window_width,params.nt_photometry_posttime,window,[],NaN);
%         end % light
% 
%         measures.fp.t = dfof_t{1,1}; % perhaps we should keep t light dependent
%         mask_post = measures.fp.t > 0;
%         mask_pre = measures.fp.t < 0;
%         measures.fp.(event).(channels{c}).dfof = dfof{2,c};
%         % measures.fp.(change).max_dfof = max(measures.fp.(change).dfof(ind_post));
%         % measures.fp.(change).mean_dfof = mean(measures.fp.(change).dfof(ind_post));
%         % measures.fp.(change).range_dfof = max(measures.fp.(change).dfof(ind_post))-min(measures.fp.(change).dfof(ind_post));
% 
%         measures.fp.(event).(channels{c}).zscore = zscore{2,c};
%         % measures.fp.(change).max_zscore = max(measures.fp.(change).zscore(ind_post));
%         % measures.fp.(change).mean_zscore = mean(measures.fp.(change).zscore(ind_post));
%         % measures.fp.(change).range_zscore = max(measures.fp.(change).zscore(ind_post))-min(measures.fp.(change).zscore(ind_post));
% 
%         measures.fp.(event).(channels{c}).dfof_isos = dfof{1,c};
%         % measures.fp.(change).max_dfof_isos = max(measures.fp.(change).dfof_isos(ind_post));
%         % measures.fp.(change).mean_dfof_isos = mean(measures.fp.(change).dfof_isos(ind_post));
%         % measures.fp.(change).range_dfof_isos = max(measures.fp.(change).dfof_isos(ind_post))-min(measures.fp.(change).dfof_isos(ind_post));
% 
%         measures.fp.(event).(channels{c}).zscore_isos = zscore{1,c};
%         % measures.fp.(change).max_zscore_isos = max(measures.fp.(change).zscore_isos(ind_post));
%         % measures.fp.(change).mean_zscore_isos = mean(measures.fp.(change).zscore_isos(ind_post));
%         % measures.fp.(change).range_zscore_isos = max(measures.fp.(change).zscore_isos(ind_post))-min(measures.fp.(change).zscore_isos(ind_post));
%     end % channel c
% end % change i
% 
% 
