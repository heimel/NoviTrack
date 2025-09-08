function record = analyse_nttestrecord(record,verbose)
%analyse_nttestrecord Analyses neurotar experiment
%
%  RECORD = analyse_nttestrecord( RECORD, [VERBOSE=true])
%
%  See nt_data_structures.md for more information.
%
% 2023-2025, Alexander Heimel, Zhiting Ren

if nargin<2 || isempty(verbose)
    verbose = true;
end

params = nt_default_parameters( record );

if ~isempty(params.nt_seed)
    rng(params.nt_seed);
end

nt_data = nt_load_tracking_data(record);

% [nt_data,neurotar_filename] = nt_load_neurotar_data(record);
% if isempty(nt_data)
%     nt_data = nt_load_mouse_tracks(record);
% end
% if isempty(nt_data)
%      nt_data = nt_load_DLC_data(record);
% end

if isempty(nt_data)
    logmsg(['Could not any position data for ' recordfilter(record)]);
end

logmsg(['Analyzing ' recordfilter(record)]);


if isempty(nt_data) && params.automatically_track_mouse 
    time_range = [];
     record = nt_track_mouse(record,time_range,verbose);
end

%% Check-out markers
if nt_check_markers( record, params, verbose ) == false
    return
end

record.measures.snippets_tbins = (-params.nt_photometry_pretime + params.nt_photometry_bin_width/2):params.nt_photometry_bin_width:(params.nt_photometry_posttime-params.nt_photometry_bin_width/2);

%% Photometry analysis
[record,photometry] = nt_analyse_photometry(record,nt_data,verbose);

snippets = [];
if ~isempty(photometry) 
    snippets = nt_make_photometry_snippets(photometry,record.measures,params);
end

%% Motion analysis
snippets = nt_make_motion_snippets(nt_data,record.measures,snippets,params);

filename = fullfile(nt_session_path(record),'nt_snippets.mat');
save(filename,'snippets');


%% Compute event measures
record.measures = nt_compute_event_measures(snippets,record.measures,params);


%% Object independent session measures
measures = record.measures;

if isempty(nt_data)
    logmsg('No nt_data to analyze.')
    return
end

mask = (nt_data.Time>0);
n_samples = sum(mask);

measures.session_speed_mean = mean(nt_data.Speed(mask),'omitnan');
measures.session_speed_std = std(nt_data.Speed(mask),'omitnan');
measures.session_speed_max = max(nt_data.Speed(mask));
measures.session_forward_speed_mean = mean(nt_data.Forward_speed(mask),'omitnan');
measures.session_forward_speed_std = std(nt_data.Forward_speed(mask),'omitnan');
measures.session_forward_speed_max = max(nt_data.Forward_speed(mask));
measures.session_angular_velocity_mean = mean(nt_data.Angular_velocity(mask),'omitnan');
measures.session_angular_velocity_std = std(nt_data.Angular_velocity(mask),'omitnan');
measures.session_angular_velocity_max = max(nt_data.Angular_velocity(mask));

measures.session_fraction_running_forward = sum( nt_data.Forward_speed(mask)> params.nt_min_approach_speed ) / n_samples;
measures.session_count_start_running_forward = sum( diff(nt_data.Forward_speed(mask) > params.nt_min_approach_speed )>0);
measures.session_start_running_forward_per_min = measures.session_count_start_running_forward / nt_data.Time(end) * 60;

measures.session_fraction_moving_backward = sum( nt_data.Forward_speed(mask) < params.nt_min_retreat_speed ) / n_samples;
measures.session_count_start_moving_backward = sum( diff(nt_data.Forward_speed(mask) < params.nt_min_retreat_speed )>0);
measures.session_start_moving_backward_per_min = measures.session_count_start_moving_backward / nt_data.Time(end) * 60;

record.measures = measures;

record = nt_compute_locations(record,nt_data,verbose);


if ~params.neurotar
    return
    % Below this only works for one object
end

%% Object analysis
[record,nt_data] = nt_object_analysis(record,nt_data,verbose);
measures = record.measures;
% if ~isempty(neurotar_filename)
%     save([neurotar_filename  '.mat'],'nt_data');
% end

%% Compute shuffles for object analysis
if isfield(measures,'object_positions') && ~isempty(measures.object_positions)

    for b = 1:length(params.nt_behaviors)
        behavior = params.nt_behaviors(b).behavior;
        measures.(behavior).shuffles_count_in_interaction_period = [];
        measures.(behavior).shuffles_fraction_in_interaction_period = [];
    end % b
    for i = 1:length(params.nt_indices)
        index = params.nt_indices(i).index;
        measures.(index).shuffles = [];
    end % i
    for r = 1:length(params.nt_rates)
        rate = params.nt_rates(r).rate;
        measures.(rate).shuffles_time = [];
        measures.(rate).shuffles_mean = [];
    end % r

    % Shuffle object insertions
    for i = 1:params.nt_shuffle_number
        logmsg(['Shuffle ' num2str(i) ' of ' num2str(params.nt_shuffle_number)])
        shuffle_record = shuffle_object_insertions( record,nt_data,params );
        shuffle_record = nt_object_analysis(shuffle_record,nt_data,false);

        for b = 1:length(params.nt_behaviors)
            behavior = params.nt_behaviors(b).behavior;
            measures.(behavior).shuffles_count_in_interaction_period = ...
                [measures.(behavior).shuffles_count_in_interaction_period shuffle_record.measures.(behavior).count_in_interaction_period];
            measures.(behavior).shuffles_fraction_in_interaction_period = ...
                [measures.(behavior).shuffles_fraction_in_interaction_period shuffle_record.measures.(behavior).fraction_in_interaction_period];
        end % b

        for j = 1:length(params.nt_indices)
            index = params.nt_indices(j).index;
            measures.(index).shuffles(i) = shuffle_record.measures.(index).val;
        end % j

        for r = 1:length(params.nt_rates)
            rate = params.nt_rates(r).rate;
            measures.(rate).shuffles_time = [measures.(rate).shuffles_time shuffle_record.measures.(rate).time];
            measures.(rate).shuffles_mean = [measures.(rate).shuffles_mean shuffle_record.measures.(rate).mean];
        end % r
    end % shuffle i

    % compute mean rates for shuffles
    for r = 1:length(params.nt_rates)
        rate = params.nt_rates(r).rate;
        [~,ind] = sort(measures.(rate).shuffles_time);
        [measures.(rate).shuffles_mean,measures.(rate).shuffles_time,measures.(rate).shuffles_sem] = ...
            slidingwindowfunc(measures.(rate).shuffles_time(ind), measures.(rate).shuffles_mean(ind), ...
            -3, 0.1, params.nt_interaction_period,params.nt_object_sliding_window,'nanmean');
    end % r
else
    logmsg('No object positions given. Retrack?');
end
record.measures = measures;

end

%% Help functions

function shuffle_record = shuffle_object_insertions( record, neurotar_data, params )
% Shuffles object markers and positions into new record
shuffle_record = record;

if ~params.neurotar
    logmsg('SHUFFLE STILL NEEDS TO BE UPDATED FOR FREELY WALKING. DISABLED')
    return
end

neurotar_duration = neurotar_data.Time(end);
measures = record.measures;

ind = find([record.measures.markers.marker]~='o' & ...
    [record.measures.markers.marker]~='t' & ...
    [record.measures.markers.marker]~='v' & ...
    [record.measures.markers.marker]~='h' & ...
    [record.measures.markers.marker]~='f');
measures.markers(ind) = [];
if measures.markers(end).marker~=params.nt_stop_marker
    % Add stop marker at the end
    measures.markers(end+1).marker = params.nt_stop_marker;
    measures.markers(end).time = neurotar_data.Time(end);
end
shuffle_record.measures = measures;


if params.nt_shuffle_insert_object_only_when_stationary

    if 0 % new method
        stationary = abs(neurotar_data.Forward_speed < params.nt_maximum_stationarity_speed);
        stationary(1) = false; % set moving at start
        stationary(end) = false; % set moving at start
        start_stationary = find(diff(stationary)>0);
        end_stationary = find(diff(stationary)<0);
        stationary_period = neurotar_data.Time(end_stationary) - neurotar_data.Time(start_stationary);
        ind_suitable_periods = find(stationary_period > params.nt_shuffle_stationary_period);
        if isempty(ind_suitable_periods)
            errormsg('Too few long enough stationary periods for shuffling. Consider lowering params.nt_shuffle_stationary_period');
            return
        end

        logmsg('NOT FINISHED IMPLEMENTING NEW METHOD YET')

    else % old method
        random_timeshift = 0;

        m = 1;
        while m<=length(measures.markers)
            if contains('ovhf', measures.markers(m).marker)
                moving = true;
                splitup = true;
                while moving || splitup
                    random_timeshift = neurotar_duration*rand(1);
                    shuffle_record.measures.markers(m).time = mod(measures.markers(m).time + random_timeshift,neurotar_duration);
                    ind = find(neurotar_data.Time>shuffle_record.measures.markers(m).time-params.nt_shuffle_stationary_period & neurotar_data.Time<shuffle_record.measures.markers(m).time );
                    moving = any(abs(neurotar_data.Forward_speed(ind)) > params.nt_max_stationarity_speed);
                    ind_take_out = m + find([measures.markers(m+1:end).marker]=='t',1);
                    splitup = (mod(measures.markers(ind_take_out).time + random_timeshift,neurotar_duration) < shuffle_record.measures.markers(m).time);
                end
            else
                shuffle_record.measures.markers(m).time = mod(measures.markers(m).time + random_timeshift,neurotar_duration);
            end

            % shift object positions
            if m<length(measures.markers)
                ind = find( measures.object_positions(:,1) > measures.markers(m).time & measures.object_positions(:,1) < measures.markers(m+1).time);
            else
                ind = find( measures.object_positions(:,1) > measures.markers(m).time);
            end
            for j = ind(:)'
                shuffle_record.measures.object_positions(j,1) = mod(shuffle_record.measures.object_positions(j,1) + random_timeshift,neurotar_duration);
                shuffle_record.measures.object_positions(j,[2 3]) = shuffle_record.measures.object_positions(j,[3 2]);  % swap x and y
            end

            m = m + 1;
        end
    end
else
    random_timeshift = neurotar_duration*rand(1);
    for m = 1:length(measures.markers)
        shuffle_record.measures.markers(m).time = mod(measures.markers(m).time + random_timeshift,neurotar_duration);
    end

    % shift object positions accordingly
    shuffle_record.measures.object_positions(:,1) = mod(record.measures.object_positions(:,1) + random_timeshift,neurotar_duration);
    shuffle_record.measures.object_positions(:,[2 3]) = record.measures.object_positions(:,[3 2]);  % swap x and y

end

% resort markers
[~,ind] = sort([shuffle_record.measures.markers(:).time]);
shuffle_record.measures.markers = shuffle_record.measures.markers(ind);

% resort object positions
[~,ind] = sort(shuffle_record.measures.object_positions(:,1));
shuffle_record.measures.object_positions = shuffle_record.measures.object_positions(ind,:);


end


