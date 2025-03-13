%optimize_get_mouse_position. Script to optimize parameters for nt_get_mouse_position
%
% 2025, Alexander Heimel

%%
load('testimage.mat','frame','bg','params','mask');

% params.wc_blackThreshold = 0.4;
% params.wc_minMajorAxisLength = 120;
% params.wc_maxMouseSize = 6000; % pxl, Max area that could be mouse
% params.wc_maxAreaSize = 8000; % pxl, Max area that could be mouse
% params.wc_minAreaSize = 200; % pxl, Minimal area for region that is tracked as mouse
% params.wc_minMouseSize = 4000; % pxl, Minimal area a mouse could be
% params.wc_minStimSize = 0; % pxl, Minimal area for region that might be stimulus
% params.wc_tailWidth = 20; % pxl
% params.wc_tailToMiddle = 70; % pxl
% params.wc_minComponentSize = 6; % pxl, Consider smaller components as noise
% params.wc_dilation = ones(5); % for image dilation
% params.wc_bg_normalization = 20;


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

n_stim = 2;
prev_mousepos = [];
prev_stimpos = [];

figure
hold on
h = image(frame);
axis image
set(gca,'ydir','reverse')

[mousepos,stimpos,mouse_boundary,stat] = ...
    nt_get_mouse_position(frame,bg,n_stim,params,h,mask,...
    prev_mousepos,prev_stimpos );
stat

%%
load('C:\Users\alexa\OneDrive\Projects\Ren\Innate_approach\Data_collection\23.35.05\nttestdb_23.35.05_alexander.mat')
time_range = [];
verbose = false;
[record,stat] = nt_track_mouse(db(3),time_range,verbose);
%record = nt_track_mouse(db(2),time_range,arena_rect,verbose);