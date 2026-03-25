function [markers,stim_id] = nt_insert_marker( markers, t, marker, params, verbose, handles)
%nt_insert_marker. Insert marker into marker struct array
%
%  [markers,stim_id] = nt_insert_marker( markers, t, marker, params, verbose)
%
% 2025, Alexander Heimel

if nargin<6 || isempty(handles)
    handles = [];
end
    
if nargin<5 || isempty(verbose)
    verbose = false;
end
    
ind = find_record(params.markers,['marker=' marker(1)]);
if isempty(ind)
    logmsg(['Unknown marker ' marker '. Not inserted the marker.']);
    stim_id = [];
    return
end


if params.markers(ind).linked
    if length(marker)==2
        stim_id = str2double(marker(2));
    elseif params.neurotar 
        stim_id = 1; % don't ask
    else
        stim_id = nt_ask_stim_id(handles);
    end
    marker = [marker(1) num2str(stim_id)];
else 
    stim_id = [];
end

if verbose
    logmsg(['Inserting marker ''' marker ''' at time ' num2str(t)])
end

if isempty(markers)
    markers(1).time = t;
    markers(1).marker = marker;
    return
end

mt = [markers.time];

% check if marker already exists
ind = find(mt==t);
if ~isempty(ind)
   % if strcmp(markers(ind).marker,marker)
    if contains(marker,{markers(ind).marker})
        logmsg(['Marker ' marker ' already present at t = ' num2str(t) '. Not inserting again'])
        return
    end
end

% insert marker at proper time
ind = find(mt<t,1,'last'); 
if isempty(ind)
    markers(2:end+1) = markers;
    markers(1).time = t;
    markers(1).marker = marker;
else
    markers(ind+2:end+1) = markers(ind+1:end);
    markers(ind+1).time = t;
    markers(ind+1).marker = marker;
end
end
