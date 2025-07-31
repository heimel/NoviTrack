function folder = nt_fiber_photometry_folder(record)
%nt_fiber_photometry_folder. Returns foldername containing fiber photometry data
%
% 2025, Alexander Heimel
 
params = nt_default_parameters(record);

folder = fullfile(params.networkpathbase,record.project,'Data_collection',record.dataset,record.subject,record.sessionid);
if ~exist(folder,'dir')
    record.sessionid = [subst_specialchars(record.date) '_' record.subject  ...
        '_' record.condition];

    folder = fullfile(params.networkpathbase ,record.project,'Data_collection',record.dataset,record.sessionid);
end

d = dir(fullfile(folder,'Fluorescence-unaligned.csv'));
if isempty(d)
    d = dir(fullfile(folder,'20*'));
    if isempty(d)
        logmsg(['Cannot find fiber photometry data for ' recordfilter(record)]);
        return
    end
    folder = fullfile(folder,d.name);
end