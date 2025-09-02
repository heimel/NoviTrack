function record = nt_analyse_photometry(record,verbose)
%nt_analyse_photometry. Analyse fiber photometry signal time locked to markers
%
%   RECORD = nt_analyse_photometry(RECORD,VERBOSE=true)
%
% 2025, Alexander Heimel

if nargin<2 || isempty(verbose)
    verbose = true;
end

if isempty(record.measures)
    logmsg('No trigger_times in measures. Run Track first.');
    return
end

% Temporary. Can go when all data is updated.
if isfield(record.measures,'trigger_times') && iscell(record.measures.trigger_times)
    logmsg('Old format of trigger_times (before 2025-06-28). Re-open track first.')
    return
end

params = nt_default_parameters( record );

[photometry,measures] = nt_load_photometry(record,params);

[photometry,measures] = nt_preprocess_photometry(photometry,measures,params);

[snippets,measures] = nt_make_photometry_snippets(photometry,measures,params);

measures = nt_compute_photometry_measures(snippets,measures,params);

filename = fullfile(nt_photometry_folder(record),'nt_photometry.mat');
save(filename,'photometry','snippets');
logmsg(['Saved photometry analysis in ' filename]);

record.measures = measures;
end
