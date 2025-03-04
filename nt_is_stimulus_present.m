function stimulus_present = nt_is_stimulus_present(markers,t,stimulus_types)
%nt_is_stimulus_present. Returns if particular stimuli is present at certain time
%
%   stimulus_present = nt_is_stimulus_present(markers,t,[stimulus_types=params.nt_stim_markers])
%
%    interpreting marker 't' as LIFO!
%
% 2024, Alexander Heimel

logmsg('DEPRECATED SHOULD BE REMOVED')

if nargin<3 || isempty(stimulus_types)
    params = nt_default_parameters();
    stimulus_types = params.nt_stim_markers;
end
if iscell(stimulus_types)
    stimulus_types = [stimulus_types{:}];
end


present_stimuli = '';
m = 1;
while m<=length(markers) && markers(m).time < t
    switch markers(m).marker
        case 't'
            if isempty(present_stimuli)
                logmsg(['Marker indicating stimulus removed, but no stimuli present at time ' num2str(markers(m).time)]);
            else
                present_stimuli(end) = '';
            end
        otherwise
            present_stimuli(end+1) = markers(m).marker; %#ok<AGROW>
    end
    m = m + 1;
end % while

stimulus_present = any(ismember(stimulus_types,present_stimuli));

