function nt_show_markers(markers,ax,params,bounds,yl)
%nt_show_markers. Show marker on a timeline
%
%  nt_show_markers(MARKERS,AX,PARAMS,[BOUNDS=xlim],[YL=ylim])
%
% 2023-2025, Alexander Heimel

if ~params.nt_show_markers 
    return;
end

if nargin<4 || isempty(bounds)
    bounds = xlim(ax);
end
if nargin<5 || isempty(yl)
    yl = ylim(ax);
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
    ind = find_record(params.markers,['marker=' markers(i).marker(1)]);
    if ~isempty(ind)
        color = params.markers(ind).color;
        if params.markers(ind).behavior && ~params.nt_show_behavior_markers
            continue
        end
    else
        color = [0 0 0];
    end
  %  plot(ax,markers(i).time*[1 1],yl,'-','Color',color,'LineWidth',1,'Tag','Marker');
    line(ax,markers(i).time*[1 1],yl,'Color',color,'LineWidth',1,'Tag','Marker');
end
end
