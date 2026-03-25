function [folder,found] = nt_photometry_folder(record)
% nt_photometry_folder. Returns foldername containing photometry data
%
%    [FOLDER,FOUND] = nt_photometry_folder(RECORD)
%          FOUND is true if photometry data found in FOLDER.
%
% 2025, Alexander Heimel
 
found = false;

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
    d = d([d.isdir]);
    if isempty(d)
        logmsg(['Cannot find photometry data for ' recordfilter(record)]);
        return
    end
    if length(d)>1
        logmsg(['Not sure which folder to pick for photometry data. Picking first folder for ' recordfilter(record)]);
    end

    folder = fullfile(folder,d(1).name);
end

if ~exist(fullfile(folder, "Fluorescence-unaligned.csv"),'file')
    logmsg(['Cannot find photometry data for ' recordfilter(record)]);
    return
else
    found = true;
end
