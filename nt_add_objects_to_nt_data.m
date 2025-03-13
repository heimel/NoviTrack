function nt_data = nt_add_objects_to_nt_data( record, nt_data )
%nt_add_objects_to_nt_data. Add object times and relative positions to nt_data
%
%  nt_data = nt_add_objects_to_nt_data( RECORD, params.nt_data )
%
% 2023-2024, Alexander Heimel

logmsg(['Adding objects to nt_data for ' recordfilter(record)])

params = nt_default_parameters( record );
measures = record.measures;

if isfield(measures,'object_positions')
    if size(measures.object_positions,2)~=5 % old format
        errormsg(['Old object positions format. To update retrack record ' recordfilter(record)],false)
        return
    end
    object_positions = measures.object_positions;
else
    logmsg(['No objects found for ' recordfilter(record)]);
    object_positions = [];
end

n_samples = length(nt_data.Time);

% Compute time since object placement
nt_data.Time_since_object_placement = NaN(n_samples,1);
time_object_inserts = [];
time_object_removes = [];
object_present = false;

for m = 1:length(measures.markers)
    switch measures.markers(m).marker(1)
        case params.nt_stim_markers
            if object_present
                time_object_removes(end+1) = measures.markers(m).time; %#ok<AGROW> 
            end
            time_object_inserts(end+1) = measures.markers(m).time;  %#ok<AGROW>
            object_present = true;
        case params.nt_stop_marker
            if object_present
                time_object_removes(end+1) = measures.markers(m).time;  %#ok<AGROW>
            end
            object_present = false;
    end
end % m
if object_present
    time_object_removes(end+1) = nt_data.Time(end);
end
time_prev_object_removes = [-Inf time_object_removes(1:end-1)];
n_objects = length(time_object_inserts);
for i = 1:n_objects
    ind = find(nt_data.Time>time_prev_object_removes(i) & nt_data.Time<time_object_removes(i));
    nt_data.Time_since_object_placement(ind) = nt_data.Time(ind) - time_object_inserts(i);
end

% Merge object extractions into object positions
ind = find_record(measures.markers,['marker=' params.nt_stop_marker]);
for i = ind(:)'
    object_positions(end+1,:) = [measures.markers(i).time NaN NaN params.ARENA 1]; %#ok<AGROW> % obj_id = 1 
end
if ~isempty(object_positions)
    [~,ind] = sort(object_positions(:,1));
    object_positions = object_positions(ind,:);
end

% Set object positions
nt_data.Object_X = NaN(n_samples,1); % in arena coordinates
nt_data.Object_Y = NaN(n_samples,1); % in arena coordinates
nt_data.Object_X_neurotar = NaN(n_samples,1); % in neurotar/mouse coordinates
nt_data.Object_Y_neurotar = NaN(n_samples,1); % in neurotar/mouse coordinates
if ~isempty(object_positions)
    current_object_position = [NaN NaN params.ARENA 1]; % obj_id = 1
    next_ind = 1;
    for i=1:n_samples
        if nt_data.Time(i) > object_positions(next_ind,1)
            current_object_position = object_positions(next_ind,2:end);
            next_ind = next_ind + 1;
            if next_ind>size(object_positions,1)
                nt_data.Object_X(i:end) = NaN;
                nt_data.Object_Y(i:end) = NaN;
                nt_data.Object_X_neurotar(i:end) = NaN;
                nt_data.Object_Y_neurotar(i:end) = NaN;
                break
            end
        end
        if ~isnan(current_object_position(1))
            switch current_object_position(3)
                case params.ARENA
                    nt_data.Object_X(i) = current_object_position(1);
                    nt_data.Object_Y(i) = current_object_position(2);
                    [nt_data.Object_X_neurotar(i),nt_data.Object_X_neurotar(i)] = ...
                        nt_change_arena_to_neurotar_coordinates(...
                        current_object_position(1),...
                        current_object_position(2),...
                        nt_data.X(i), nt_data.Y(i), nt_data.alpha(i), params);
                case params.NEUROTAR
                    [nt_data.Object_X(i),nt_data.Object_Y(i)] = ...
                        nt_change_neurotar_to_arena_coordinates(...
                        current_object_position(1),...
                        current_object_position(2),...
                        nt_data.X(i),nt_data.Y(i),nt_data.alpha(i),params);
                    nt_data.Object_X_neurotar(i) = current_object_position(1);
                    nt_data.Object_Y_neurotar(i) = current_object_position(2);
                case params.OVERHEAD
                    
                    [nt_data.Object_X_neurotar(i),nt_data.Object_X_neurotar(i)] = ...
                        nt_change_overhead_to_neurotar_coordinates(...
                        current_object_position(1),current_object_position(2),params);

                    [nt_data.Object_X(i),nt_data.Object_Y(i)] = ...
                        nt_change_overhead_to_arena_coordinates(...
                        current_object_position(1),...
                        current_object_position(2),...
                        nt_data.X(i),nt_data.Y(i),nt_data.alpha(i),params);
            end
            if isnan(nt_data.Object_X(i)) || isnan(nt_data.Object_Y(i))
                logmsg(['No appropriate object coordinates at ' num2str(nt_data.Time(i))]);
            end
        end

    end % sample i
end % ~isempty(object_positions)

% Compute object distance
object_x_neurotar = NaN(n_samples,1);
object_y_neurotar = NaN(n_samples,1);
for i=1:n_samples
    [object_x_neurotar(i),object_y_neurotar(i)] = ...
        nt_change_arena_to_neurotar_coordinates(nt_data.Object_X(i),...
        nt_data.Object_Y(i),...
        nt_data.X(i),nt_data.Y(i),nt_data.alpha(i),params);
end
nt_data.Object_distance = sqrt( object_x_neurotar.^2 + (object_y_neurotar - params.neurotar_snout_distance_mm).^2 );

nt_data.Object_distance = smoothen(nt_data.Object_distance,params.nt_temporal_filter_width);
nt_data.Object_distance_derivative = -[NaN;diff(nt_data.Object_distance)./diff(nt_data.Time)]; %mm/s?

% Compute relative angular velocity
nt_data.Object_angle = angle( object_y_neurotar - 1i*object_x_neurotar); % positive to left hand side
nt_data.Angular_velocity_towards_object = sign(nt_data.Object_angle) .* nt_data.Angular_velocity;

