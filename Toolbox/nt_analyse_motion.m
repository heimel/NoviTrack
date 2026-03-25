function [record,snippets] = nt_analyse_motion(record,nt_data,verbose)
%nt_analyse_motioin. Analyse motion time locked to markers
%
%   [RECORD,SNIPPETS] = nt_analyse_motion(RECORD,[NT_DATA],[VERBOSE=true])
%
%  DEPRECATED REMOVE
%
% 2025, Alexander Heimel

if nargin<2 || isempty(nt_data)
    nt_data = [];
end
if nargin<3 || isempty(verbose)
    verbose = true;
end

[snippets,measures] = nt_make_motion_snippets(nt_data,measures,params);

filename = fullfile(nt_session_path(record),'nt_motion.mat');
save(filename,'snippets');
logmsg(['Saved motion snippets in ' filename]);
