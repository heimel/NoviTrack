function [neurotar_data,neurotar_filename] = nt_load_neurotar_data(record)
%nt_load_neurotar_data Loads neurotar data from tdms or mat file
%
%  NEUROTAR_DATA = nt_load_neurotar_data( RECORD )
%       NEUROTAR_DATA contains a table with the original neurotar data, 
%       supplemented by additional columns 'Time, 'Forward_speed',
%       'Angular_velocity'.
%
%       Time = Since_track_start - First trigger in Since_track_start.
%       So, when using Time, first trigger is a Time = 0.
%
%   NEUROTAR_DATA.Speed is in m/s (rather than in mm/s as in original file)
%
%  
%  Check neurotar_data_explanation.md for more information.
%
% 2023, Alexander Heimel

neurotar_data = [];
neurotar_filename = [];

params = nt_default_parameters(record);

neurotar_path = fullfile(params.networkpathbase,record.project,'Data_collection','Neurotar');
neurotar_mask = fullfile(neurotar_path,['Track_[' record.date '*]_' record.subject '_session' num2str(record.sessnr)]);
d = dir(neurotar_mask);
if isempty(d) && strcmp(record.subject,'exampleVideo')
    neurotar_path = fullfile(params.networkpathbase,record.project,'Data_collection','Neurotar','exampleVideos');
    neurotar_mask = fullfile(neurotar_path,['Track_[' record.date '*]_' record.subject '_session' num2str(record.sessnr)]);
    d = dir(neurotar_mask);
end

if isempty(d)
    %logmsg(['Cannot find Neurotar data in ' neurotar_mask]);
    return
end
if length(d)>1
    errormsg(['Cannot decide which data to use. Two folders matching ' neurotar_mask]);
    return
end
neurotar_sessionname = d(1).name;

neurotar_filename = fullfile(neurotar_path, neurotar_sessionname, [neurotar_sessionname(1:find(neurotar_sessionname==']',1)) ]);
if exist([neurotar_filename  '.mat'],'file')
    logmsg(['Loading neurotar data ' neurotar_filename '.mat']);
    load([neurotar_filename  '.mat'],'neurotar_data');
else
    logmsg(['Loading neurotar data ' neurotar_filename '.tdms']);
    tdmsdata = tdmsDatastore([neurotar_filename '.tdms']);
    tdmsdata.SelectedChannelGroup = "Pp_Data";
    neurotar_data = readall(tdmsdata);
    neurotar_data = neurotar_data{1};
end

if istable(neurotar_data)
    % convert from table to struct of arrays, because it is way faster
    neurotar_data = convert_table_to_struct( neurotar_data);
    save([neurotar_filename  '.mat'],'neurotar_data');
end

% check for end session for and remove everything after end session
if ~isempty(record.measures) && isfield(record.measures,'markers')
    ind = find_record( record.measures.markers,'marker=e');
    if ~isempty(ind) % found end session marker
        logmsg(['Removing all data after end of session marker at ' num2str(record.measures.markers(ind).time,2) ' s.'])
        ind = ind(1);
        n_samples = find(neurotar_data.Time<record.measures.markers(ind).time,1,'last');
        flds = fields(neurotar_data);
        for f = 1:length(flds)
            neurotar_data.(flds{f})(n_samples+1:end) = [];
        end
    end
end

%

neurotar_trigger_frames = find(neurotar_data.TTL_outputs==1);
neurotar_trigger_frames = [neurotar_trigger_frames(1) ...
    neurotar_trigger_frames(diff(neurotar_trigger_frames)>1) ...
    length(neurotar_data.Since_track_start)]; % add last frame as off-trigger

neurotar_trigger_times = neurotar_data.Since_track_start(neurotar_trigger_frames);
neurotar_data.Time = neurotar_data.Since_track_start-neurotar_trigger_times(1);


% Change Speed to SI
neurotar_data.Speed = neurotar_data.Speed / 1000; % Change from mm/s to m/s


% Compute forward speed
rx = -sin(neurotar_data.alpha/180*pi);
ry = cos(neurotar_data.alpha/180*pi);
dx = [0; diff(neurotar_data.X)];
dy = [0; diff(neurotar_data.Y)];
neurotar_data.Forward_speed = (rx.*dx + ry.*dy)./[1; diff(neurotar_data.Time)];
neurotar_data.Forward_speed = smoothen(neurotar_data.Forward_speed,params.nt_temporal_filter_width);

% Compute angular velocity
complex_alpha = exp(1i*neurotar_data.alpha/180*pi);
d_alpha = complex_alpha(2:end)./complex_alpha(1:end-1);
neurotar_data.Angular_velocity = [0; angle(d_alpha)/pi*180]./[1; diff(neurotar_data.Time)]; % deg/s
neurotar_data.Angular_velocity = smoothen(neurotar_data.Angular_velocity,params.nt_temporal_filter_width);

% Compute distance to wall
neurotar_data.Distance_to_wall = thresholdlinear(params.arena_radius_mm - neurotar_data.R); 

% 
n_samples = length(neurotar_data.Time);

if ~isfield(neurotar_data,"Object_distance")
    neurotar_data.Object_distance = NaN(n_samples,1);
end

% to match freely moving fields
neurotar_data.CoM_X = NaN(n_samples,1);
neurotar_data.CoM_Y = NaN(n_samples,1);
neurotar_data.tailbase_X = NaN(n_samples,1);
neurotar_data.tailbase_Y = NaN(n_samples,1);


neurotar_data.Coordinates = params.ARENA;

end

function neurotar_data = convert_table_to_struct( neurotar_data_table)
flds = neurotar_data_table.Properties.VariableNames;
for i = 1:length(flds)
    fld = flds{i};
    neurotar_data.(fld) = neurotar_data_table.(fld);
end
end