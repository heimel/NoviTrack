function sessions = myGetSessions(varargin)
%myGetSessions is wrapper around FYD getSessions that does not fail if FYD cannot be reached
%
%  sessions = myGetSessions(varargin)
%    example myGetSessions(project='Innate_approach',dataset='22.35.01')
%
% 2022, Alexander Heimel

if canConnectFYD
    sessions = getSessions(varargin{:});
    return
end

p = inputParser;
addOptional(p,'project','-',@(x)validateattributes(x,{'char'},{'nonempty'}))
addOptional(p,'dataset','-',@(x)validateattributes(x,{'char'},{'nonempty'}))
addOptional(p,'excond','-',@(x)validateattributes(x,{'char'},{'nonempty'}))
addOptional(p,'subject','-',@(x)validateattributes(x,{'char'},{'nonempty'}))
addOptional(p,'stimulus','-',@(x)validateattributes(x,{'char'},{'nonempty'}))
addOptional(p,'setup','-',@(x)validateattributes(x,{'char'},{'nonempty'}))
addOptional(p,'date','-',@(x)validateattributes(x,{'char'},{'nonempty'}))

parse(p,varargin{:})

p.Results

pth = networkpathbase();
if ~strcmp(p.Results.project,'-')
    pth = fullfile(pth,p.Results.project);
end

sessions = collect_session_json_files(pth);
