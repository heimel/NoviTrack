function nt_list_markers(input)
%nt_list_markers. Lists markers in record, measures, or markers struct
%
%   nt_list_markers(input)
%
% 2024, Alexander Heimel


if isfield(input,'project')
    markers = input.measures.markers;
elseif isfield(input,'markers')
    markers = input.markers;
else
    markers = input;
end

if isempty(markers)
    logmsg('No markers')
    return
end

disp('Markers')
for m = 1:length(markers)
    fprintf('%9.3f,  %s\n',markers(m).time,markers(m).marker)    
end
