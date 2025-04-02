function [record,neurotar_data] = nt_object_analysis(record,neurotar_data,verbose)
%nt_object_analysis Computes forward speed and relations to objects
%
%  RECORD = nt_object_analysis( RECORD, [NEUROTAR_DATA], [VERBOSE = true] )
%
%  2023, Alexander Heimel

logmsg('DEPRECATED. ONLY WORKS FOR ONE OBJECT')

if nargin<2 || isempty(neurotar_data)
    neurotar_data = nt_load_neurotar_data(record);
end
if nargin<3 || isempty(verbose)
    verbose = true;
end

if isempty(neurotar_data)
    logmsg(['Could not load neurotar data for ' recordfilter(record)])
    return
end

params = nt_default_parameters( record );

measures = record.measures;

if isempty(measures)
    logmsg('Track first.')
    return
end
if verbose
    logmsg(['Object analysis of ' recordfilter(record)]);
end
if ~isfield(measures,'markers') || isempty(measures.markers) 
    logmsg(['Nothing to do. No markers in ' recordfilter(record)]);
    return
end

n_samples = length(neurotar_data.Time);
sample_time = (neurotar_data.Time(end)-neurotar_data.Time(1))/(n_samples-1);

neurotar_data = nt_add_objects_to_nt_data( record, neurotar_data );



%% Compute behaviors
measures.behaviors = struct([]);
for b = 1:length(params.nt_behaviors)
    behavior = params.nt_behaviors(b).behavior;
    vals = compute_behavior(neurotar_data,behavior,params);
    start_behavior = ([diff(vals);0]>0);
    stop_behavior = ([diff(vals);0]<0);

    in_interaction_period = (neurotar_data.Time_since_object_placement>0 & neurotar_data.Time_since_object_placement<params.nt_interaction_period);

    measures.(behavior).fraction_in_interaction_period = sum( vals & in_interaction_period ) / sum( in_interaction_period );
    


    measures.(behavior).start_time = neurotar_data.Time(start_behavior);
    measures.(behavior).stop_time = neurotar_data.Time(stop_behavior);
    if ~params.count_once_per_object
        measures.(behavior).count_in_interaction_period = sum( start_behavior & in_interaction_period );
    else
        markers = [measures.markers.marker];
        ind = find(markers=='o' | markers=='v' | markers=='f' | markers=='h' | markers=='i' );
        count = 0;
        for i = 1:length(ind)
           start = measures.markers(ind(i)).time;
           if ind(i) < length(measures.markers)
               stop =  measures.markers(ind(i)+1).time;
           else
               stop = Inf;
           end
           count = count + any(start_behavior & in_interaction_period & neurotar_data.Time > start & neurotar_data.Time < stop) ;

        end % i 
        measures.(behavior).count_in_interaction_period = count;
    end
end

%% Compute indices
measures.indices = struct([]);
for i = 1:length(params.nt_indices)
    index = params.nt_indices(i).index;
    measures.(index) = [];
    measures.(index).val = compute_index(measures,index);
end

%% Compute peri-object rates
ind = find(neurotar_data.Time_since_object_placement>-3 & neurotar_data.Time_since_object_placement<params.nt_interaction_period);
time_since_object_placement = neurotar_data.Time_since_object_placement(ind);
[time_since_object_placement ,ind2] = sort(time_since_object_placement);
ind = ind(ind2);

for i = 1:length(params.nt_rates)
    rate = params.nt_rates(i).rate;
    vals = neurotar_data.(capitalize(rate))(ind);
    [measures.(rate).mean,measures.(rate).time,measures.(rate).sem] = ...
        slidingwindowfunc(time_since_object_placement, vals, ...
        -3, 0.1, params.nt_interaction_period, params.nt_object_sliding_window,'nanmean');
    measures.(rate).sem = measures.(rate).sem * sqrt(params.nt_object_sliding_window / sample_time); % correct for multiple samples in window
end

record.measures = measures;

end

function val = compute_index(measures,index)
switch index
    case 'run_retreat_count_balance'
        val = measures.run.count_in_interaction_period  / (measures.run.count_in_interaction_period + measures.retreat.count_in_interaction_period + 0.00001);
    case 'turn_count_balance'
        val = measures.turn_towards.count_in_interaction_period / (measures.turn_towards.count_in_interaction_period + measures.turn_away.count_in_interaction_period + 0.00001) ;
    case 'run_retreat_fraction_balance'
        val = measures.run.fraction_in_interaction_period / (measures.run.fraction_in_interaction_period + measures.retreat.fraction_in_interaction_period + 0.00001);
    case 'turn_fraction_balance'
        val = measures.turn_towards.fraction_in_interaction_period / (measures.turn_towards.fraction_in_interaction_period + measures.turn_away.fraction_in_interaction_period + 0.00001) ;
end
end


function  vals = compute_behavior(neurotar_data,behavior,params)
switch behavior
    case 'run'
        vals = (neurotar_data.Forward_speed > params.nt_min_run_speed );
    case 'retreat'
        vals = (neurotar_data.Forward_speed < params.nt_min_retreat_speed );
    case 'turn_towards'
        vals = (neurotar_data.Angular_velocity_towards_object > params.nt_min_angular_velocity & abs(neurotar_data.Forward_speed) < params.nt_max_stationarity_speed  );
    case 'turn_away'
        vals = (neurotar_data.Angular_velocity_towards_object < -params.nt_min_angular_velocity & abs(neurotar_data.Forward_speed) <params.nt_max_stationarity_speed );
    case 'leave_wall'
        vals = (neurotar_data.Distance_to_wall > params.nt_max_distance_to_wall);
    case 'approach'
        vals = (neurotar_data.Object_distance_derivative > params.nt_min_approach_speed & neurotar_data.Forward_speed > 0 );
    case 'avoid'
        vals = (neurotar_data.Object_distance_derivative < params.nt_min_retreat_speed & neurotar_data.Forward_speed < 0);
    case 'touch'
        vals = (neurotar_data.Object_distance < params.nt_max_touching_distance);
end
end

