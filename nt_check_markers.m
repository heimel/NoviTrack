function correct = nt_check_markers( record, params, verbose )
%nt_check_markers. Checks if markers are self-consistent
%
% CORRECT = nt_check_markers( RECORD,PARAMS,[VERBOSE=TRUE])
%    return CORRECT = true if markers are self-consistent, otherwise
%    CORRECT = false.
%
% 2023-2024, Alexander Heimel

if nargin<2 || isempty(params)
    params = nt_default_parameters(record);
end
if nargin<3 || isempty(verbose)
    verbose = true;
end

correct = true;

measures = record.measures;

if isempty(measures) || ~isfield(measures,'markers')
    return
end

stimulus_present = false;
for m = 1:length(measures.markers)
    switch measures.markers(m).marker
        case 't'
            if ~stimulus_present
                msg = ['Stimulus stopped before starting at ' num2str(measures.markers(m).time,2) ' s'];
                correct = false;
                break
            end
            stimulus_present = false;
        case params.nt_stimulus_types 
            if stimulus_present
                msg = ['Stimulus started twice at ' num2str(measures.markers(m).time,2) ' s'];
                correct = false;
                break
            end
            stimulus_present = true;
    end
end  % m

if ~correct && verbose
    errormsg([msg ' in' recordfilter(record)])
end
