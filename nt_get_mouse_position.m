function [mousepos,stimpos,mouse_boundary,stat] = nt_get_mouse_position(frame,bg,n_stim,params,handles,mask,prev_mousepos,prev_stimpos,verbose)
%NT_GET_MOUSE_POSITION gets mouse centroid, tail, nose, stim in pixels
%
%  [MOUSEPOS,STIMPOS,BOUNDARY,STAT] = nt_get_mouse_position( FRAME,BG,[PARAMS],[HFIG],[MASK],[N_STIM],[PREV_MOUSEPOS],[PREV_STIMPOS] )
%
%      MOUSE_POSITION is mouse position struct
%         .com = center of mass
%         .tailbase 
%         .nose
%      MASK is a logical image with the arena marked as true. 
%      STIMPOS = Nx3, with x,y,stim_id center of mass info for N objects
%      PREV_STIMPOS = Nx3, with x,y,stim_id center of mass info for N objects
%      STAT is a struct with some info about the mouse area
%
% 2017, Laila Blomer
% 2019-2025, Alexander Heimel

persistent sedisk

if nargin<9 || isempty(verbose)
    verbose = false;
end
if nargin<8 || isempty(prev_stimpos)
    prev_stimpos = [];
end
if nargin<7 || isempty(prev_mousepos)
    prev_mousepos = [];
end
if nargin<6 || isempty(mask)
    mask = [];
end
if nargin<5
    handles = [];
end
if nargin<4 || isempty(params)
    params.nt_black_threshold = 0.4;
    params.nt_min_mouse_length = 120;
    params.nt_max_mouse_area = 5000; % pxl, Max area that could be mouse
    params.nt_min_component_area = 200; % pxl, Minimal area for component to be relevant
    params.nt_min_mouse_area = 4000; % pxl, Minimal area a mouse could be
    params.nt_min_stim_size = 0; % pxl, Minimal area for region that might be stimulus
    params.nt_max_tail_width = 20; % pxl, Max tail width (to find tailbase)
    params.nt_min_tail_distance = 70; % pxl, Minimal distance of tailbase to mouse C.o.M.
    params.nt_dilation = ones(5); % for image dilation
    params.nt_bg_normalization = 20;
    params.nt_min_black_threshold = 0.01;

end
if nargin<3 || isempty(n_stim)
    if isempty(prev_stimpos)
        n_stim = 0;
    else
        n_stim = size(prev_stimpos,1);
    end
end

if isempty(sedisk)
    % precompute dilation disks
    for i=1:6
        sedisk{i} = strel('disk',5*i);
    end
end

mousepos = struct('com',[NaN NaN],'tailbase',[NaN NaN],'nose',[NaN NaN],'tailtip',[NaN NaN]);
stimpos = [];


bg = double(bg);
frame_bg_subtracted = bg - double(frame);
frame_bg_subtracted = abs(frame_bg_subtracted);
frame_bg_subtracted = frame_bg_subtracted ./ (bg + params.nt_bg_normalization);
frame_bg_subtracted = max(frame_bg_subtracted,[],3); % make it grayscale

if ~isempty(handles)
    % handles.image.CData = frame_bg_subtracted;
    %imagesc(frame_bg_subtracted);
    %hold on
    %colormap gray
end

pos = []; % will contain component areas
black_threshold = params.nt_black_threshold;


matched_criteria = false;
while  ~matched_criteria && black_threshold>params.nt_min_black_threshold
    black_threshold = 0.9*black_threshold; % lower threshold

    imbw = (frame_bg_subtracted > black_threshold);
    if ~isempty(mask)
        imbw = imbw.*mask;
    end
    %imbw = imclose(imbw,params.nt_dilation);
    cc = bwconncomp(imbw);

    if length(cc.PixelIdxList)<(1+n_stim)
        matched_criteria = false;
        continue
    end
    pos = regionprops(cc,'Area');
    matched_criteria =  ...
        sum([pos.Area])>(params.nt_min_mouse_area + n_stim*params.nt_min_stim_size) && ...
        max([pos.Area])>params.nt_min_mouse_area  && ...
        max([pos.Area])<params.nt_max_mouse_area;  
    if ~matched_criteria
        continue
    end

    [~,ind] = max([pos.Area]);
    cc_one.Connectivity = cc.Connectivity;
    cc_one.ImageSize = cc.ImageSize;
    cc_one.NumObjects = 1;
    cc_one.PixelIdxList = cc.PixelIdxList(ind);
    mal = regionprops(cc_one,'MajorAxisLength');

    matched_criteria = (mal.MajorAxisLength>params.nt_min_mouse_length);
end

if black_threshold<params.nt_min_black_threshold
    if verbose
        logmsg([char(datetime('now')) ': Failed to meet criteria'])
    end
    black_threshold = 0.2362;
    imbw = frame_bg_subtracted> black_threshold;
    if ~isempty(mask)
        imbw = imbw.*mask;
    end
    %imbw = imclose(imbw,params.nt_dilation);
    cc = bwconncomp(imbw);
end

stat.black_threshold = black_threshold;
stat.mouse_area = NaN;
stat.mouse_length = NaN;
stat.matched_criteria = NaN;

mouse = imbw;
pos = regionprops(cc,'Centroid','Area');
if isempty(pos) || not(any([pos.Area]>params.nt_min_component_area))
    if verbose        
        logmsg('Could not find any changed components');
    end
    mouse_boundary = [];
    return
end


[~,ind] = sort([pos.Area],'descend'); % sort by size, largest first
cc.PixelIdxList = cc.PixelIdxList(ind);
pos = pos(ind);

% get mouse center
% assume mouse is largest component
indmouse = 1;
mousepos.com = pos(indmouse).Centroid;

    


% get stim centers (n_stim large enough objects, larger than minStimSize and not mouse)
if n_stim>0
    indstim = find([pos.Area]>params.nt_min_stim_size,n_stim+1);
    indstim = indstim(2:end); % remove mouse component

    for i=1:length(indstim)
        stimpos(i,[1 2]) = pos(indstim(i)).Centroid;
        stimpos(i,3) = i; % provisional stim_id
    end

    if ~isempty(prev_stimpos)
        % change stim_id to closest previous stim_id
        stimpos(:,3) = NaN;

        n_prev_stim = size(prev_stimpos,1);
        n_stim_found = size(stimpos,1);
        d = NaN(n_prev_stim,n_stim_found);
        for i=1:n_prev_stim
            for j=1:n_stim_found
                d(i,j) = sum( (prev_stimpos(i,[1 2])-stimpos(j,[1 2])).^2 );
            end % j
        end % i

        while any(~isnan(d(:)))
            [~,ind] = min(d(:));
            [i,j] = ind2sub(size(d),ind);
            stimpos(j,3) = prev_stimpos(i,3);
            d(i,:) = NaN;
            d(:,j) = NaN;
        end

        % add other stim_ids to unidentified objects
        ids = 1:9;
        ids([prev_stimpos(:,3)]) = [];
        ind = find(isnan(stimpos(:,3)));
        stimpos(ind,3) = ids(ind);
    end

    if ~isempty(handles)
        for i = 1:size(stimpos,1)                
            % plot(stimpos(i,1),stimpos(i,2),'ro');
            handles.stim(stimpos(i,3)).Position([1 2]) = stimpos(i,[1 2]); 
            % text(stimpos(i,1),stimpos(i,2),num2str(stimpos(i,3)),...
            %     'HorizontalAlignment','Center','Color',[1 1 1]);
        end
    end

    
end


% Get mouse boundaries
% design new binary image with 1 shape, the mouse. Also make new
% mouseBoundaries

% boundary = bwboundaries(mouse);
 [M, N] = size(mouse);
% mouseBinary = false(size(mouse));
% for i = indmouse(:)'
%     mouseBinary = mouseBinary | poly2mask(boundary{i}(:,2), boundary{i}(:,1), M, N);
% end
% mouseBoundary = boundary(indmouse);

mouseBinary = false(size(mouse));
mouseBinary(cc(indmouse).PixelIdxList{1}) = true;
mouse_boundary = bwboundaries(mouseBinary);

% if ~isempty(hfig)
%     for i = 1:length(mouseBoundary)
%         plot(mouseBoundary{i}(:,2),mouseBoundary{i}(:,1),'y')
%     end
% end

% d = 1;
% if length(indmouse)>1 % mouse is multiple components
%     cc.NumObjects = length(indmouse);
%     while cc.NumObjects && d <length(sedisk) % grow until single component
%         mouseBinary = imclose(mouseBinary,sedisk{d});
%         cc = bwconncomp(mouseBinary);
%         d = d + 1;
%     end
%     mouseBoundary = bwboundaries(mouseBinary);
% end

A = cellfun('size', mouse_boundary, 1);
[~, ind] = max(A);
mouse_boundary = mouse_boundary{ind};
row = size(mouse_boundary,1);

if ~isempty(handles)
    %plot(mouse_boundary(:,2),mouse_boundary(:,1),'c')

    handles.mouse_boundary.XData = mouse_boundary(:,2);
    handles.mouse_boundary.YData = mouse_boundary(:,1);
    
end

stat.mouse_area = pos(indmouse).Area;
cc.NumObjects = 1;
cc.PixelIdxList = cc.PixelIdxList(1); % Notice change of cc
stat.mouse_length = getfield(regionprops(cc,'MajorAxisLength'),'MajorAxisLength');
stat.matched_criteria = matched_criteria;

% Find tail
% find farthest geodesic point from mouse c.o.m. and check if it is far
% enough from mouse centre.
D = bwdistgeodesic(mouseBinary, floor(mousepos.com(1)), floor(mousepos.com(2)), 'quasi-euclidean');
posTails = D(:);

[num,indD] = max(posTails);
if isnan(num) || (num == 0)
    tail_not_found = true;
else
    [ytailtip,xtailtip] = ind2sub(size(D),indD);
    if pdist([mousepos.com; [xtailtip, ytailtip]]) < params.nt_min_tail_distance
        % tailtip too close to centroid
        tail_not_found = true;
    else
        tail_not_found = false;
    end
end

if tail_not_found
    if verbose
        logmsg('Did not find tail');
    end
    if ~isempty(prev_mousepos) && isfield(prev_mousepos,'tailtip') && all(~isnan(prev_mousepos.tailtip))
        xtailtip = prev_mousepos.tailtip(1);
        ytailtip = prev_mousepos.tailtip(2);
        if verbose
            logmsg('Taking previous tailtip');
        end
    else
        return
    end
end
mousepos.tailtip = [xtailtip ytailtip];

if ~isempty(handles)
    handles.tailtip.XData = xtailtip;
    handles.tailtip.YData = ytailtip;
    
    %plot(xtailtip,ytailtip,'r*');
end

% take nose at the point furthers away from the tail tip
D = bwdistgeodesic(mouseBinary, xtailtip, ytailtip, 'quasi-euclidean');
posnose = D(:);
[~,indD] = max(posnose);
[mousepos.nose(2),mousepos.nose(1)] = ind2sub(size(D),indD);

if ~isempty(handles)
    handles.nose.XData = mousepos.nose(1);
    handles.nose.YData = mousepos.nose(2);
    % plot(mousepos.nose(1),mousepos.nose(2),'gx');
end

% Compute distance between found tail and every point of mouseBoundary
% to get the coordinate with the minimum distance, which should be the tip
np = length(mouse_boundary(:,1));
Pp = [ytailtip xtailtip];

% matrix of distances between all points and all vertices
dpv(:,:) = hypot((repmat(mouse_boundary(:,1)', [np 1])-repmat(Pp(:,1), [1 1])),...
    (repmat(mouse_boundary(:,2)', [np 1])-repmat(Pp(:,2), [1 1])));

% Find the vector of minimum distances to vertices.
[~, index] = min(abs(dpv),[],2);
ind = index(1);
firstInd = ind;
left = ind;
right = ind;
halfway = round(mod(ind + (row / 2), row));

% Beginning of tail
% Look for beginning of tail by following the mouse boundary untill
% distance between the two sides become larger than tailWidth.
beginFound = false;
while ~beginFound && ~tail_not_found
    left = mod((left + row - 2), row) + 1;
    right = mod(right, row) + 1;
    dist = pdist([mouse_boundary(left,:); mouse_boundary(right,:)]);
    if dist > params.nt_max_tail_width
        beginFound = true;
        ind = right;
    elseif (left == halfway) || (right == halfway)
        tail_not_found = true;
    end
end


if tail_not_found % did not find tail base
    return
end

% Separate tail and body
% Check if the end of the mouseBoundary is passed or not. Based on this,
% devide the mouse in the binary image in the body and the tail

passEnd = 0;
if ind > firstInd
    dif = ind - firstInd;
    tailB = mod(firstInd - dif, row);
    tailE = ind;
    if tailB == 0
        tailB = 1;
    end
else
    dif = firstInd - ind;
    tailB = ind;
    tailE = mod(firstInd + dif, row);
    if tailE == 0
        tailE = row;
    end
end

if tailB > tailE
    passEnd = true;
end

% separate tail and body
if passEnd
    fulltail = vertcat(mouse_boundary(tailB:end, :),mouse_boundary(1:tailE, :));
    rest = mouse_boundary(tailE:tailB, :);
else
    fulltail = mouse_boundary(tailB:tailE, :);
    rest = vertcat(mouse_boundary(tailE:end, :), mouse_boundary(1:tailB, :));
end

% Find new tail and mouse positions

% new tail position
mousepos.tailbase(1) = mean([fulltail(1,2)  fulltail(end,2)]);
mousepos.tailbase(2) = mean([fulltail(1,1)  fulltail(end,1)]);

if ~isempty(handles)
    handles.tailbase.XData = mousepos.tailbase(1);
    handles.tailbase.YData = mousepos.tailbase(2);

    %plot(mousepos.tailbase(1),mousepos.tailbase(2),'rx');
end

% new mouse binary mask
tailBinary = poly2mask(fulltail(:,2), fulltail(:,1), M, N);
mouseNew = poly2mask(rest(:,2), rest(:,1), M, N);

% if there are multiple shapes in the binary image, make a new image
% with only the largest shape
temp = bwconncomp(mouseNew);
if temp.NumObjects > 1
    numPixels = cellfun(@numel,temp.PixelIdxList);
    [~ ,idx] = max(numPixels);
    temp2 = zeros(size(mouse));
    temp2(temp.PixelIdxList{idx}) = 1;
    mouseNew = logical(temp2);
end

% only if the body is bigger than the tail, take the new mouse position
% from the centre of the body.
if (sum(tailBinary(:)) < sum(mouseNew(:)))
    posNew = regionprops(mouseNew, 'Centroid');
    mousepos.com = posNew.Centroid;
end

if ~isempty(handles)
    handles.com.XData = mousepos.com(1);
    handles.com.YData = mousepos.com(2);

    %plot(mousepos.com(1),mousepos.com(2),'c+');
    %hold off
end

    

