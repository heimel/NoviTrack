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

if isempty(measures)
    logmsg('No trigger_times in measures. Run Track first.');
    return
end

% Temporary. Can go when all data is updated.
if ~isempty(measures) && isfield(measures,'trigger_times') && iscell(measures.trigger_times)
    logmsg('Old format of trigger_times (before 2025-06-28). Re-open track first.')
    return
end

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

triggers_fp = nt_load_rwd_triggers(record);

if isempty(triggers_fp)
    logmsg('No recorded RWD triggers. Assuming 0.');
    triggers_fp = 0;
end

% align fp time to marker time
fluorescence.time = nt_change_times(fluorescence.TimeStamp,triggers_fp,measures.trigger_times);

%% isosbestic control


measures.fit_isos = cell(n_channels,1);
for ch=1:n_channels
    channel = channels{ch};
    time = fluorescence.time(fluorescence.Lights==470);
    f_signal = fluorescence.(channel)(fluorescence.Lights==470);
    f_iso = fluorescence.(channel)(fluorescence.Lights==410);


    % for regression, remove first and last 5% of data
    mask = true(size(f_signal));
    mask(1:round(length(mask)*0.05)) = false;
    mask(end-round(length(mask)*0.05):end) = false;
    f_signal = f_signal(mask);
    f_iso = f_iso(mask);
    time = time(mask);

    % Linear regression: F_signal ≈ a * F_iso + b
    X = [f_iso ones(size(f_iso))];
    measures.fit_isos{ch} = X \ f_signal;  % Least-squares solution

    % use all data again
    time = fluorescence.time(fluorescence.Lights==470);
    f_signal = fluorescence.(channel)(fluorescence.Lights==470);
    f_iso = fluorescence.(channel)(fluorescence.Lights==410);
    X = [f_iso ones(size(f_iso))];

    f_artifact = X * measures.fit_isos{ch};


    figure('Name',['Raw ' channel],'NumberTitle','off');
    subplot('position',[0.1 0.01 0.8 0.05])
    text(0,0,recordfilter(record));
    axis off
    
    ax1 = subplot(2,1,1);
    hold on
    plot(time,f_signal,'g')
    plot(time,f_artifact,'b')
    ylabel('Fluorescence (a.u.)')
    xlabel('Time (s)')
    title(channel)

%    nt_show_markers(markers,ax,params,bounds,yl)
    nt_show_markers(measures.markers,ax1,params,[],[])

    ax2 = subplot(2,1,2);
    hold on
    plot(time,f_signal-f_artifact,'k')
    ylabel('Corrected fluorescence (a.u.)')
    xlabel('Time (s)')
    nt_show_markers(measures.markers,ax2,params,[],[])

end
if params.nt_apply_isosbestic_correction
    for ch=1:n_channels
        channel = channels{ch};
        f_iso = fluorescence.(channel)(fluorescence.Lights==410);
        X = [f_iso ones(size(f_iso))];
        f_artifact = X * measures.fit_isos{ch};
        fluorescence.(channel)(fluorescence.Lights==470) = fluorescence.(channel)(fluorescence.Lights==470) - f_artifact;
    end % ch
end
measures.applied_isosbestic_correction = params.nt_apply_isosbestic_correction;



%% Produce snippets

% the name changes is a leftover from an earlier function. here it
% indicates the marker

events = table([measures.markers.time]',string({measures.markers.marker}'),'VariableNames',{'time','event'});
unique_events = unique(events.event);
measures.unique_events = unique_events;


n_bins_per_event = (params.nt_photometry_pretime + params.nt_photometry_posttime) ...
    / params.nt_photometry_bin_width;
fp.t_bins = (-params.nt_photometry_pretime + params.nt_photometry_bin_width/2):params.nt_photometry_bin_width:(params.nt_photometry_posttime-params.nt_photometry_bin_width/2);

measures.fp = [];
for i = 1:length(unique_events)
    event = unique_events(i);
    ind = find(events.event==event);
    n_events = length(ind);
    measures.fp.(event).n_events = n_events;
     
    dfof = cell(n_lights,n_channels);
    dfof_t = cell(n_lights,n_channels);

    for c = 1:n_channels
        channel = channels{c};

        t = cell(n_lights,1);
        f = cell(n_lights);
        f_baseline = cell(n_lights);

        fp.(event).(channel).peristimulus = zeros(n_lights,n_events,n_bins_per_event);

        for light = 1:n_lights
            for j = 1:n_events
                event_time = events.time(ind(j));
                mask_pre = ...
                    fluorescence.time>(event_time - params.nt_photometry_pretime) & ...
                    fluorescence.time<event_time & ...
                    fluorescence.Lights==lights(light);

                mask_post = ...
                    fluorescence.time>=event_time  & ...
                    fluorescence.time<(event_time + params.nt_photometry_posttime) & ...
                    fluorescence.Lights==lights(light);

                 mask_all = mask_pre | mask_post;

                % vq = interp1(x,v,xq)
                fp.(event).(channel).peristimulus(light,j,:) = ...
                    interp1( fluorescence.time(mask_all)-event_time,...
                    fluorescence.(channel)(mask_all),fp.t_bins);

                t{light} = [t{light}; fluorescence.time(mask_all)-event_time];

                f0 = mean(fluorescence.(channel)(mask_pre));

                f{light} = [f{light}; (fluorescence.(channel)(mask_all) - f0)/f0];
                f_baseline{light} = [f_baseline{light}; (fluorescence.(channel)(mask_pre) - f0)/f0]; % used for z-scoring
            end % event j


            [t{light},ind_t] = sort(t{light});
            f{light} = f{light}(ind_t);

            window = max(median(diff(t{light})),0.1);

            [dfof{light,c},dfof_t{light,c}] = slidingwindowfunc(t{light},f{light},...
                -params.nt_photometry_pretime,params.nt_photometry_window_width,params.nt_photometry_posttime,window,[],NaN);

            m = mean(f_baseline{light});
            s = std(f_baseline{light});
            z = (f{light}-m)/s;

            zscore{light,c} = slidingwindowfunc(t{light},z,...
                -params.nt_photometry_pretime,params.nt_photometry_window_width,params.nt_photometry_posttime,window,[],NaN);
        end % light

        measures.fp.t = dfof_t{1,1}; % perhaps we should keep t light dependent
        mask_post = measures.fp.t > 0;
        mask_pre = measures.fp.t < 0;
        measures.fp.(event).(channels{c}).dfof = dfof{2,c};
        % measures.fp.(change).max_dfof = max(measures.fp.(change).dfof(ind_post));
        % measures.fp.(change).mean_dfof = mean(measures.fp.(change).dfof(ind_post));
        % measures.fp.(change).range_dfof = max(measures.fp.(change).dfof(ind_post))-min(measures.fp.(change).dfof(ind_post));

        measures.fp.(event).(channels{c}).zscore = zscore{2,c};
        % measures.fp.(change).max_zscore = max(measures.fp.(change).zscore(ind_post));
        % measures.fp.(change).mean_zscore = mean(measures.fp.(change).zscore(ind_post));
        % measures.fp.(change).range_zscore = max(measures.fp.(change).zscore(ind_post))-min(measures.fp.(change).zscore(ind_post));

        measures.fp.(event).(channels{c}).dfof_isos = dfof{1,c};
        % measures.fp.(change).max_dfof_isos = max(measures.fp.(change).dfof_isos(ind_post));
        % measures.fp.(change).mean_dfof_isos = mean(measures.fp.(change).dfof_isos(ind_post));
        % measures.fp.(change).range_dfof_isos = max(measures.fp.(change).dfof_isos(ind_post))-min(measures.fp.(change).dfof_isos(ind_post));

        measures.fp.(event).(channels{c}).zscore_isos = zscore{1,c};
        % measures.fp.(change).max_zscore_isos = max(measures.fp.(change).zscore_isos(ind_post));
        % measures.fp.(change).mean_zscore_isos = mean(measures.fp.(change).zscore_isos(ind_post));
        % measures.fp.(change).range_zscore_isos = max(measures.fp.(change).zscore_isos(ind_post))-min(measures.fp.(change).zscore_isos(ind_post));
    end % channel c
end % change i

filename = fullfile(folder,'novitrack_fp.mat');
save(filename,'fp');
logmsg(['Save peristimulus fluorescence in ' filename]);


%% Clean up

record.measures = measures;