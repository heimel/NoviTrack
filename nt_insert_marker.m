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

if verbose
    logmsg(['Inserting ' params.markers(ind).description ' at time ' num2str(t)])
end

if params.markers(ind).linked
    if length(marker)==2
        stim_id = str2double(marker(2));
    elseif params.neurotar 
        stim_id = 1; % don't ask
    else
        if ~isempty(handles)
            set(handles.text_state,'String','Choose stim');
        end
        stim_id = NaN;
        while isnan(stim_id)
            fprintf('Choose which stim_id (1,2,...) by pressing number key: ')
            drawnow
            waitforbuttonpress;
            key = get(gcf,'CurrentCharacter');
            fprintf([key '\n']);
            stim_id = str2double(key);
            if isnan(stim_id)
                disp([key ' is not a digit. Choose again.']);
            end
        end
    end
    marker = [marker(1) num2str(stim_id)];
else 
    stim_id = [];
end

if isempty(markers)
    markers(1).time = t;
    markers(1).marker = marker;
    return
end

% insert marker at proper time
mt = [markers.time];
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
