function [mousepos,stimpos,mouseBoundary] = nt_get_mouse_position(frame,bg,n_stim,params,hfig,area_rect,prev_mousepos,prev_stimpos )
%NT_GET_MOUSE_POSITION gets mouse centroid, tail, nose, stim in pixels
%
%  [POS,TAILBASE,nose,STIMPOS] = nt_get_mouse_position( FRAME,BG,[PARAMS],[HFIG],[AREA_RECT],[N_STIM],[PREV_MOUSEPOS],[PREV_STIMPOS] )
%
%      MOUSE_POSITION is mouse position struct
%         .com = center of mass
%         .tailbase 
%         .nose
%
%      STIMPOS = Nx3, with x,y,stim_id center of mass info for N objects
%      PREV_STIMPOS = Nx3, with x,y,stim_id center of mass info for N objects
%
%
%
% 2017, Laila Blomer
% 2019-2025, Alexander Heimel

persistent sedisk

if nargin<8 || isempty(prev_stimpos)
    prev_stimpos = [];
end
if nargin<7 || isempty(prev_mousepos)
    prev_mousepos = [];
end
if nargin<6 || isempty(area_rect)
    % taking full frame as screen rectangle
    area_rect = [0 0 size(frame,2) size(frame,1)];
end
if nargin<5
    hfig = [];
end
if nargin<4 || isempty(params)
    params.wc_minAreaSize = 200; % pxl, Minimal area for region that is tracked as mouse
    params.wc_minMouseSize = 50^2; % pxl, Minimal area a mouse could be
    params.wc_minStimSize = 10; % pxl, Minimal area for region that might be stimulus
    params.wc_tailWidth = 12; % pxl
    params.wc_tailToMiddle = 70; % pxl
    params.wc_minComponentSize = 10; % pxl, Consider smaller components as noise
    params.wc_dilation = ones(5); % for image dilation
    params.wc_blackThreshold = 0.3;
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

mousepos = struct('com',[NaN NaN],'tailbase',[NaN NaN],'nose',[NaN NaN]);
stimpos = [];


bg = double(bg);
frame_bg_subtracted = bg - double(frame);
frame_bg_subtracted = abs(frame_bg_subtracted);
frame_bg_subtracted = frame_bg_subtracted ./ (bg + params.wc_bg_normalization);
frame_bg_subtracted = max(frame_bg_subtracted,[],3); % make it grayscale

if ~isempty(hfig)
    imagesc(frame_bg_subtracted);
    hold on
    colormap gray
end

pos = []; % will contain component areas
blackThreshold = params.wc_blackThreshold;

while ( ...
        length(pos)<(1+n_stim) || ...
        sum([pos.Area])<(params.wc_minMouseSize + n_stim*params.wc_minStimSize) || ...
        max([pos.Area])<params.wc_minMouseSize )...
        && blackThreshold>0.01
    imbw = (frame_bg_subtracted > blackThreshold);
    imbw = imclose(imbw,params.wc_dilation);
    cc = bwconncomp(imbw);
    pos = regionprops(cc,'Area');
    blackThreshold = 0.9*blackThreshold; % lower threshold


    % logmsg(['blackThreshold: ' num2str(blackThreshold) ...
    %     ' #components: ' num2str(length(pos)) ...
    %     ' total area: ' num2str(sum([pos.Area])) ...
    %     ' max area: ' num2str(max([pos.Area])) ...
    %     ])
end

imbw = frame_bg_subtracted> blackThreshold;
imbw = imclose(imbw,params.wc_dilation);

mouse = imbw;
cc = bwconncomp(imbw);
pos = regionprops(cc,'Centroid','Area');
if isempty(pos) || not(any([pos.Area]>params.wc_minAreaSize))
    logmsg('Could not find any changed components');
    return
end


[~,ind] = sort([pos.Area],'descend'); % sort by size, largest first
cc.PixelIdxList = cc.PixelIdxList{ind};
pos = pos(ind);


% get mouse center
% indmouse = find([pos.Area]>params.wc_minAreaSize);
% posCentroids = [pos(indmouse).Centroid];
% mousepos = [ posCentroids(1:2:end)*[pos(indmouse).Area]'/sum([pos(indmouse).Area]), ...
%     posCentroids(2:2:end)*[pos(indmouse).Area]'/sum([pos(indmouse).Area])];
%
% assume mouse is largest component
indmouse = 1;
mousepos.com = pos(indmouse).Centroid;

% if ~isempty(hfig)
%     plot(mousepos.com(1),mousepos.com(2),'og'); % TEMPORARY
% end


% get stim centers (n_stim large enough objects, larger than minStimSize and not mouse)
if n_stim>0
    indstim = find([pos.Area]>params.wc_minStimSize,n_stim+1);
    indstim = indstim(2:end); % remove mouse component

    for i=1:length(indstim)
        stimpos(i,[1 2]) = pos(indstim(i)).Centroid;
        stimpos(i,3) = i; % provisional stim_id
    end

    if ~isempty(prev_stimpos)
        % change stim_id to closest previous stim_id
        
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

        if length(find(stimpos(:,3)==1))>1
            keyboard
        end
    end

    if ~isempty(hfig)
        for i = 1:length(indstim)
            % plot(stimpos(i,1),stimpos(i,2),'ro');
            text(stimpos(i,1),stimpos(i,2),num2str(stimpos(i,3)),...
                'HorizontalAlignment','Center','Color',[1 1 1]);
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
mouseBinary(cc(indmouse).PixelIdxList) = true;
mouseBoundary = bwboundaries(mouseBinary);

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

A = cellfun('size', mouseBoundary, 1);
[~, ind] = max(A);
mouseBoundary = mouseBoundary{ind};
row = size(mouseBoundary,1);

if ~isempty(hfig)
    plot(mouseBoundary(:,2),mouseBoundary(:,1),'c')
end

% Find tail
% find farthest geodesic point from mouse c.o.m. and check if it is far
% enough from mouse centre.
D = bwdistgeodesic(mouseBinary, floor(mousepos.com(1)), floor(mousepos.com(2)), 'quasi-euclidean');
posTails = D(:);

[num,indD] = max(posTails);
if isnan(num) || (num == 0)
    tailNotFound = true;
else
    [ytailtip,xtailtip] = ind2sub(size(D),indD);
    if pdist([mousepos.com; [xtailtip, ytailtip]]) < params.wc_tailToMiddle
        % tailtip too close to centroid
        tailNotFound = true;
    else
        tailNotFound = false;
    end
end

if tailNotFound
    %logmsg('Did not find tail');
    return
end

if ~isempty(hfig)
    plot(xtailtip,ytailtip,'r*');
end

% take nose at the point furthers away from the tail tip
D = bwdistgeodesic(mouseBinary, xtailtip, ytailtip, 'quasi-euclidean');
posnose = D(:);
[~,indD] = max(posnose);
[mousepos.nose(2),mousepos.nose(1)] = ind2sub(size(D),indD);

if ~isempty(hfig)
    plot(mousepos.nose(1),mousepos.nose(2),'gx');
end

% Compute distance between found tail and every point of mouseBoundary
% to get the coordinate with the minimum distance, which should be the tip
np = length(mouseBoundary(:,1));
Pp = [ytailtip xtailtip];

% matrix of distances between all points and all vertices
dpv(:,:) = hypot((repmat(mouseBoundary(:,1)', [np 1])-repmat(Pp(:,1), [1 1])),...
    (repmat(mouseBoundary(:,2)', [np 1])-repmat(Pp(:,2), [1 1])));

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
while ~beginFound && ~tailNotFound
    left = mod((left + row - 2), row) + 1;
    right = mod(right, row) + 1;
    dist = pdist([mouseBoundary(left,:); mouseBoundary(right,:)]);
    if dist > params.wc_tailWidth
        beginFound = true;
        ind = right;
    elseif (left == halfway) || (right == halfway)
        tailNotFound = true;
    end
end

if tailNotFound % did not find tail base
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
    fulltail = vertcat(mouseBoundary(tailB:end, :),mouseBoundary(1:tailE, :));
    rest = mouseBoundary(tailE:tailB, :);
else
    fulltail = mouseBoundary(tailB:tailE, :);
    rest = vertcat(mouseBoundary(tailE:end, :), mouseBoundary(1:tailB, :));
end

% Find new tail and mouse positions

% new tail position
mousepos.tailbase(1) = mean([fulltail(1,2)  fulltail(end,2)]);
mousepos.tailbase(2) = mean([fulltail(1,1)  fulltail(end,1)]);

if ~isempty(hfig)
    plot(mousepos.tailbase(1),mousepos.tailbase(2),'rx');
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

if ~isempty(hfig)
    plot(mousepos.com(1),mousepos.com(2),'c+');
    hold off
end
