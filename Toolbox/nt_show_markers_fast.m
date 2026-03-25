function nt_show_markers_fast(markers,ax,params,bounds,yl)
%nt_show_markers_fast. Updates markers on a timeline, assuming only time increased
%
%  nt_show_markers_fast(MARKERS,AX,PARAMS,BOUNDS,YL)
%
% 2025, Alexander Heimel

if ~params.nt_show_markers 
    return;
end

if isempty(markers)
    return
end

c = get(ax,'Children');
% assume latest added children are highest-time marker
if strcmp(c(1).Tag,'Marker')
    max_time = c(1).XData(1);
else
    max_time = bounds(1);
end

i = length(c);
while i>=1
    if strcmp(c(i).Tag,'Marker') 
        x = c(i).XData(1);
        if x<bounds(1) 
            delete(c(i));
        else 
            break;
        end
    end
    i = i - 1;
end

if ~strcmp(get(ax,'nextplot'),'add')
    hold(ax,"on")
end


% select markers within bounds
markers = markers([markers(:).time]>max_time & [markers(:).time]<=bounds(2));

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
    line(ax,markers(i).time*[1 1],yl,'Color',color,'LineWidth',1,'Tag','Marker');
end
end
