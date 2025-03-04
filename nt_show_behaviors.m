function nt_show_behaviors(behaviors,ax,bounds)
%nt_show_behaviors. Show behavior on a timeline
%
%  nt_show_markers(MARKERS,AX,[BOUNDS=xlim])
%
% 2023, Alexander Heimel

persistent params

if nargin<3 || isempty(bounds)
    bounds = xlim(ax);
end

if isempty(params)
    params = nt_default_parameters();
end

c = get(ax,'Children');
for i=1:length(c)
    if strcmp(c(i).Tag,'Behavior')
        delete(c(i));
    end
end
hold(ax,"on")

% select markers within bounds
if isempty(behaviors)
    return
end

behaviors = behaviors([behaviors(:).time]>=bounds(1) & [behaviors(:).time]<=bounds(2));

yl = ylim(ax);

for i=1:length(behaviors)
    ind = find_record(params.nt_behaviors,['behavior=' behaviors(i).behavior]);
    if ~isempty(ind)
        color = params.nt_behaviors(ind).color;
    else
        color = [0 0 0];
    end
    plot(ax,behaviors(i).time*[1 1],yl,'--','Color',color,'LineWidth',1,'Tag','Behavior');
end
end
