function nt_show_position_changes(positions,ax,params,bounds,yl)
%nt_show_position_changes. Show position changes on a timeline
%
%  nt_show_position_changes(MARKERS,AX,PARAMS,[BOUNDS=xlim],[YL=ylim])
%
% 2025, Alexander Heimel

if ~params.nt_show_position_changes
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
    if strcmp(c(i).Tag,'Position_change')
        delete(c(i));
    end
end
if ~strcmp(get(ax,'nextplot'),'add')
    hold(ax,"on")
end

if isempty(positions)
    return
end

% select markers within bounds
positions = positions(positions(:,1)>=bounds(1) & positions(:,1)<=bounds(2),:);

if isempty(positions)
    return
end


stimuli = unique(positions(:,5));
n_stimuli = length(stimuli);
for i = 1:n_stimuli
    stimulus = stimuli(i);
    y = yl(1) + (yl(2)-yl(1))/(n_stimuli+1)*i;
    ind = find(positions(:,5)==stimulus);
    h = text(ax,positions(ind,1),y*ones(length(ind),1),...
        num2str(positions(ind,5)),...
        'horizontalalignment','center','Tag','Position_change');
end
