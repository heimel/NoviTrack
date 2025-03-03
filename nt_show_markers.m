function nt_show_markers(markers,ax,show_behavior_markers,bounds,yl)
%nt_show_markers. Show marker on a timeline
%
%  nt_show_markers(MARKERS,AX,[SHOW_BEHAVIOR_MARKERS=true],[BOUNDS=xlim],[YL=ylim])
%
% 2023, Alexander Heimel

persistent params

if nargin<3 || isempty(show_behavior_markers)
    show_behavior_markers = true;
end
if nargin<4 || isempty(bounds)
    bounds = xlim(ax);
end
if nargin<5 || isempty(yl)
    yl = ylim(ax);
end


if isempty(params)
    params = nt_default_parameters();
end

c = get(ax,'Children');
for i=1:length(c)
    if strcmp(c(i).Tag,'Marker')
        delete(c(i));
    end
end
if ~strcmp(get(ax,'nextplot'),'add')
    hold(ax,"on")
end

if isempty(markers)
    return
end

% select markers within bounds
markers = markers([markers(:).time]>=bounds(1) & [markers(:).time]<=bounds(2));

for i=1:length(markers)
    ind = find_record(params.markers,['marker=' markers(i).marker]);
    if ~isempty(ind)
        color = params.markers(ind).color;
        if params.markers(ind).behavior && ~show_behavior_markers
            continue
        end
    else
        color = [0 0 0];
    end
    plot(ax,markers(i).time*[1 1],yl,'-','Color',color,'LineWidth',1,'Tag','Marker');
end
end
