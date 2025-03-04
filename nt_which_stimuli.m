function stim_ids = nt_which_stimuli(markers,t,params)
%nt_which_stimuli_present. Returns list of stim_id that are present.
% 
%   STIM_IDS = nt_which_stimuli_present(markers,t,params)
%
%     STIM_IDS is a 1xN vector with stim_id present at time t
%
% 2025, Alexander Heimel

stim_ids = [];

m = 1;
while m<=length(markers) && markers(m).time <= t
    if any(contains(params.nt_stim_markers,markers(m).marker(1))) % stimulus marker
        if isscalar(markers(m).marker)
            if isempty(stim_ids)
                stim_id = 1;
            else
                stim_id = max(stim_ids) + 1;
            end
        else
            % stim_id = str2double(markers(m).marker(2:end));  % slower
            stim_id = markers(m).marker(2)-48; % converts '1' to 1
            % if ismember(stim_id,stim_ids)
            %     logmsg(['Stim_id ' num2str(stim_id) ' was already present at time ' num2str(markers(m).time) ]);
            % end
        end
        if ~ismember(stim_id,stim_ids)
            stim_ids = [stim_ids stim_id]; %#ok<AGROW>
        end
    elseif markers(m).marker(1)==params.nt_stop_marker % stop marker
        if isempty(stim_ids)
            logmsg(['Marker indicating stimulus removed, but no stimuli present at time ' num2str(markers(m).time)]);
        else
            if length(markers(m).marker)==1
                stim_id = stim_ids(end);
            else
                stim_id = str2double(markers(m).marker(2:end));
            end
            if ismember(stim_id,stim_ids)
                stim_ids = setdiff(stim_ids,stim_id);
            else
                logmsg(['Marker indicating stimulus ' num2str(stim_id) ' removed, but this stimulus is not present at time ' num2str(markers(m).time)]);
            end                
        end
    end
    m = m + 1;
end % while
