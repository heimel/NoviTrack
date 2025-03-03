function pth = nt_session_path(record,params)
%nt_session_path. Returns path for movies and trigger files
%
%   pth = nt_session_path(record)
%
%   Uses params.networkpathbase as root folder, e.g. '\\vs03.herseninstituut.knaw.nl\VS03-CSF-1\Ren'
%   This can be overridden in processparams_local, e.g. params.networkpathbase = 'C:\Users\heimel.HERSENINSTITUUT\OneDrive\Desktop';
%
% 2024, Alexander Heimel

if nargin<2 || isempty(params)
    params = nt_default_parameters(record);
end

pth = fullfile(params.networkpathbase,record.project,'Data_collection',record.dataset,record.subject,record.sessionid);

