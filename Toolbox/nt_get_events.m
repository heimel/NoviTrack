function events = nt_get_events(measures,params)
%nt_get_events Create event table from NoviTrack markers.
%
%  EVENTS = nt_get_events(MEASURES,PARAMS)
%
%  Events are derived from measures.markers and should not be stored in
%  measures. Keeping only markers in saved databases avoids storing MATLAB
%  table objects, which do not round-trip cleanly through Python.
%
% 2026, Alexander Heimel

if nargin<2 || isempty(params)
    params = nt_load_parameters();
end

if isempty(measures) || ~isfield(measures,'markers') || isempty(measures.markers)
    events = table([],strings(0,1),'VariableNames',{'time','event'});
    return
end

events = table([measures.markers.time]',...
    string({measures.markers.marker}'),'VariableNames',{'time','event'});

% temporary fix for illegal field names 0 and 1
events.event(events.event == "0") = "opto_off";
events.event(events.event == "1") = "opto_on";

if params.use_clean_baseline
    i = 1;
    % remove all same events within pretime
    while i<height(events)
        events(events.time>events.time(i) & events.time<(events.time(i) + params.nt_pretime) & events.event == events.event(i),:) = [];
        i = i + 1;
    end
end

if params.use_ultraclean_baseline
    i = 1;
    % remove all events within pretime
    while i<height(events)
        events(events.time>events.time(i) & events.time<(events.time(i) + params.nt_pretime),:) = [];
        i = i + 1;
    end
end

end
