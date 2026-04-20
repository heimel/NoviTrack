function params = nt_load_parameters(record)
%nt_load_parameters Contains default parameters for neurotar analysis
%
%  PARAM = nt_load_parameters([RECORD])
%
%  Edit processparams_local for local and temporary edits to these default
%  parameters.
%
% 2023-2025, Alexander Heimel 

if nargin<1 || isempty(record)
    record = [];
    record.setup = 'neurotar';
    record.stimulus = 'none';
    record.date = char(datetime('today','Format','yyyy-MM-dd'));
end

filename = fullfile(fileparts(mfilename('fullpath')),'nt_default_parameters.yaml');
if ~exist(filename,'file')
    errormsg(['Cannot find config file '''  filename ''''],true);
end
params = yamlread(filename);

params.nt_behaviors = struct( ...
    'behavior',    fieldnames(params.nt_behaviors), ...
    'description', cellfun(@(x) x{1}, struct2cell(params.nt_behaviors), 'uni', 0), ...
    'color',       cellfun(@(x) x{2}, struct2cell(params.nt_behaviors), 'uni', 0) ...
)';

params.nt_indices = struct( ...
    'index',       fieldnames(params.nt_indices), ...
    'description', cellfun(@(x) x{1}, struct2cell(params.nt_indices), 'uni', 0), ...
    'color',       cellfun(@(x) x{2}, struct2cell(params.nt_indices), 'uni', 0) ...
)';

params.nt_rates = struct( ...
    'rate',        fieldnames(params.nt_rates), ...
    'description', cellfun(@(x) x{1}, struct2cell(params.nt_rates), 'uni', 0), ...
    'color',       cellfun(@(x) x{2}, struct2cell(params.nt_rates), 'uni', 0) ...
)';

flds = fieldnames(params.nt_marker_sets);
for i = 1:length(flds)
    field = flds{i};
    marker_set = params.nt_marker_sets.(field);
    params.nt_marker_sets.(field) = struct( ...
        'marker_id',   fieldnames(marker_set), ...
        'marker',      cellfun(@(x) x{1}, struct2cell(marker_set), 'uni', 0), ...
        'description', cellfun(@(x) x{2}, struct2cell(marker_set), 'uni', 0), ...
        'color',       cellfun(@(x) x{3}, struct2cell(marker_set), 'uni', 0), ...
        'behavior',    cellfun(@(x) x{4}, struct2cell(marker_set), 'uni', 0), ...
        'linked',      cellfun(@(x) x{5}, struct2cell(marker_set), 'uni', 0) ...
        )';
end


% params = nt_default_parameters();

if strcmpi(record.setup,'neurotar')
    params.neurotar = true; % indicates if neurotar is present
else 
    params.neurotar = false;
end

% Camera's configuration
setup = lower(record.setup);
if isempty(setup)
    setup = 'default';
end
if isfield(params.camera_sets,setup)
    params = catstruct(params,params.camera_sets.(setup));
else
    params = catstruct(params,params.camera_sets.default);
end

%% Arena
if isfield(params.arenas,setup)
    params = catstruct(params,params.arenas.(setup));
else
    params = catstruct(params,params.arenas.default);
end

% to agree with older code
if isfield(params,'overhead_neurotar_headring')
    params.overhead_neurotar_headring = params.overhead_neurotar_headring(:);
end
if isfield(params,'overhead_neurotar_center')
    params.overhead_neurotar_center = params.overhead_neurotar_center(:);
end
    
% Overrides with old values
if strcmpi(record.setup,'neurotar')
    if datetime(record.date,'inputformat','yyyy-MM-dd') <  datetime('2023-11-03','inputformat','yyyy-MM-dd')
        % before 2023-11-03
        params.neurotar_snout_distance_mm = 45; % distance from snout to center of neurotar
    end
    if datetime(record.date,'inputformat','yyyy-MM-dd') <  datetime('2023-06-21','inputformat','yyyy-MM-dd')
        % before 2023-06-21
        params.neurotar_snout_distance_mm = 0; % distance from snout to center of neurotar
    end
end

% Overrides with values from record.measures
if ~isempty(record) && isfield(record,'measures') && ~isempty(record.measures) 
    if isfield(record.measures,'overhead_neurotar_headring')
        params.overhead_neurotar_headring = record.measures.overhead_neurotar_headring;
    end
    if isfield(record.measures,'overhead_neurotar_center')
        params.overhead_neurotar_center = record.measures.overhead_neurotar_center;
    end
    if isfield(record.measures,'overhead_arena_center')
        params.overhead_arena_center = record.measures.overhead_arena_center;
    end
    if isfield(record.measures,'overhead_camera_distortion')
        params.overhead_camera_distortion = record.measures.overhead_camera_distortion;
    end
    if isfield(record.measures,'overhead_camera_shear')
        params.overhead_camera_shear = record.measures.overhead_camera_shear;
    end
    if isfield(record.measures,'overhead_camera_height')
        params.overhead_camera_height = record.measures.overhead_camera_height;
    end
    if isfield(record.measures,'overhead_camera_width')
        params.overhead_camera_width = record.measures.overhead_camera_width;
    end
    if isfield(record.measures,'overhead_camera_angle')
        params.overhead_camera_angle = record.measures.overhead_camera_angle;
    end
    if isfield(record.measures,'picamera_time_multiplier')
        params.picamera_time_multiplier = record.measures.picamera_time_multiplier;
    end
end



%% Behaviors
%params.nt_behaviors = cellfun( @(x) cell2struct(x,{'behavior','description','color'},2),behaviors);


%% Markers
% markers: 'marker','description','color','behavior','linked' (linked to
% stimulus or object)
%
% Note: behavior markers should be mutually exclusive, if you want two
% behaviors simultaneously, create a new behavior

marker_set = '';
if isfield(record,'stimulus')
    switch lower(record.stimulus)
        case 'firstandnovelobject'
            marker_set = 'default';
        case 'looming_stimulus'
            marker_set = 'looming';
    end
end
if isempty(marker_set) && isfield(record,'condition')
    switch lower(record.condition)
        case 'looming_stimulus'
            marker_set = 'looming'; 
        case 'social_behavior'
            marker_set = 'social_behavior';
    end
end
if isempty(marker_set)
    switch lower(record.setup)
        case 'neurotar'
            marker_set = 'prey_capture';
        case 'elevated_plus_maze'
            marker_set = 'elevated_plus_maze';
        otherwise
            marker_set = 'default';
    end
end

params.markers = params.nt_marker_sets.(marker_set);

mask = (~[params.markers(:).behavior]) & [params.markers(:).linked];
params.nt_stim_markers = setdiff({params.markers(mask).marker},params.nt_stop_marker);

%% Tracking
if isfield(params.tracking_presets,setup)
    params = catstruct(params,params.tracking_presets.(setup));
end

%% Load processparams_local. Keep at the end
if exist('processparams_local.m','file')
    params = processparams_local( params );
end
