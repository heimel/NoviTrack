function click_on_timeline(src, event)
%click_on_timeline. Goto time clicked on timeline
%
% 2025, Alexander Heimel

fig = get(src,'Parent');
userdata = get(fig,'UserData');
userdata.action = 'goto';
userdata.time = event.IntersectionPoint(1);
set(fig,'UserData',userdata)
end
