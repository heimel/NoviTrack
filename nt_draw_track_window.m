%% Draw figure

function handles = nt_draw_track_window(handles,record,actions,nt_data,state,measures,params)
%nt_draw_track_window. Draws tracking figure

max_time = nt_data.Time(end);

handles.fig_main = figure('units','pixels','MenuBar','none','ToolBar','none',...
    'Name',['Tracking - ' subst_ctlchars(record.sessionid)],'NumberTitle','off','WindowStyle','normal');

% Speeding up graphics management
set(handles.fig_main, 'GraphicsSmoothing',params.nt_graphicssmoothing);
set(handles.fig_main, 'Renderer', params.nt_renderer);

% Toolbar buttons
toolbar = uitoolbar(handles.fig_main);
actions = actions([actions.toolbutton_position]>0);
[~,ind] = sort([actions.toolbutton_position]);
actions = actions(ind);
handles.toggle_play_button = [];
for i = 1:length(actions)
    button = uipushtool(toolbar); 
    button.Tag = actions(i).action; % action
    set_button_icon(button,true);
    button.ClickedCallback = @callback_toolbar;
    button.Tooltip = [actions(i).tooltip ' (' actions(i).key_description ')'];
    switch actions(i).action
        case 'toggle_play'
            handles.toggle_play_button = button;
    end
end


% Labels
y = 5;
uicontrol('Style','text','String','State:','Position',[20 y 50 30],'HorizontalAlignment','right');
handles.text_state = uicontrol('Style','text','String','','Position',[70 y 80 30]);
uicontrol('Style','text','String','Time:','Position',[150 y 70 30],'HorizontalAlignment','right');
handles.text_time = uicontrol('Style','text','String','','Position',[220 y 50 30]);
uicontrol('Style','text','String','FPS:','Position',[270 y 40 30],'HorizontalAlignment','right');
handles.text_fps = uicontrol('Style','text','String','','Position',[310 y 30 30]);
uicontrol('Style','text','String','Speed:','Position',[340 y 40 30],'HorizontalAlignment','right');
handles.text_playback_speed = uicontrol('Style','text','String','','Position',[380 y 30 30]);

% Movie panels
handles.panel_video = [];
num_cameras = length(params.nt_camera_names);

for i = 1:num_cameras
    handles.panel_video(i) = subplot(2,3,i);
    hold on
    if isstruct(handles.vidobj{i})
        continue
    end
    frame = readFrame(handles.vidobj{i});
    handles.camera_image(i) = image(frame, 'Parent', handles.panel_video(i)); 
    set(handles.panel_video(i),'visible','off')
    set(handles.panel_video(i),'DataAspectRatioMode','manual')
    set(handles.panel_video(i),'DataAspectRatio',[1 1 1])
    disableDefaultInteractivity(handle(handles.panel_video(i)))

    if params.overhead_camera_rotated && i == 2
        set(gca,'ydir','normal');
        set(gca,'xdir','reverse');
    else
        set(gca,'ydir','reverse');
    end
    set(gca,'ClippingStyle','rectangle')
end
set(handles.panel_video(1),'Position',[0.02 0.4 0.25 0.4]);
set(handles.panel_video(2),'Position',[0.30 0.3 0.4 0.5]); % overhead
set(handles.panel_video(3),'Position',[0.73 0.4 0.25 0.4]);


% Panel timeline
handles.panel_timeline = subplot('Position',[0.1 0.9 0.8 0.05]);
set(gca,'ytick',[])
xlim([0 max_time]);
ylim([0 1]);
hold on
%handles.timeline_current_time = plot(state.master_time*[1 1],[0 params.nt_track_timeline_max_speed],'k-','linewidth',3);
handles.timeline_current_time = line(state.master_time*[1 1],[0 params.nt_track_timeline_max_speed],'Color',[0 0 0],'linewidth',3);

plot(nt_data.Time,rescale(nt_data.Speed,[0 params.nt_track_timeline_max_speed],[0 params.nt_track_timeline_max_speed]),'-','Color',0.7*[1 1 1]);
ylim([0 params.nt_track_timeline_max_speed]);
nt_show_markers(measures.markers,handles.panel_timeline,params);
set(handles.panel_timeline,'ButtonDownFcn',@click_on_timeline);

% Panel with neurotar speed
handles.panel_neurotar_speed = subplot('Position',[0.05 0.25 0.25 0.1]);
hold on
handles.speed_xaxis = line([0 max_time],[0 0],'Color' ,0.7*[1 1 1]);
handles.speed_yaxis = line([0 0],[-1 1],'Color' ,0.7*[1 1 1]);
disableDefaultInteractivity(handle(handles.panel_neurotar_speed))
%handles.speed_trace = plot(0,0,'-k');
handles.speed_trace = line(0,0,'Color',[0 0 0]);
set(handles.panel_neurotar_speed.XAxis,'visible','off')
ylabel('Fwd speed');
ylim(handles.panel_neurotar_speed,[-250 250]);
set(handles.panel_neurotar_speed,'ButtonDownFcn',@click_on_timeline);

% Panel with camera distortion controls
fontsize =  params.fontsize;
panel_camera_distortion = uipanel(handles.fig_main,'Position',[0.73 0.05 0.22 0.1],'Title','Matching video to neurotar');
height = fontsize*1.33*1.3;

sep = 3;
left = sep;
width = fontsize*1.33*6;
handles.edit_camera_distortion = uicontrol(panel_camera_distortion,'Style','edit',...
    'units','pixels','FontSize',fontsize,'Position',[left sep width height]);
handles.edit_camera_distortion.String = mat2str(params.overhead_camera_distortion);
handles.edit_camera_distortion.Callback = @edit_camera_distortion_callback;
uicontrol(panel_camera_distortion,'Style','text','String','Distort',...
    'units','pixels','FontSize',fontsize,'Position',[left 2*sep+height width height]);
left = left + width + sep;

width = fontsize*1.33*6;
handles.edit_camera_neurotar_center = uicontrol(panel_camera_distortion,'Style','edit',...
    'units','pixels','FontSize',fontsize,'Position',[left sep width height]);
handles.edit_camera_neurotar_center.String = mat2str(round(params.overhead_neurotar_center));
handles.edit_camera_neurotar_center.Callback = @edit_camera_distortion_callback;
uicontrol(panel_camera_distortion,'Style','text','String','Bridge',...
    'units','pixels','FontSize',fontsize,'Position',[left 2*sep+height width height]);
left = left + width + sep;


width = fontsize*1.33*4;
handles.edit_camera_angle = uicontrol(panel_camera_distortion,'Style','edit',...
    'units','pixels','FontSize',fontsize,'Position',[left sep width height]);
handles.edit_camera_angle.String = mat2str(round(params.overhead_camera_angle/pi*180));
handles.edit_camera_angle.Callback = @edit_camera_distortion_callback;
uicontrol(panel_camera_distortion,'Style','text','String','Angle',...
    'units','pixels','FontSize',fontsize,'Position',[left 2*sep+height width height]);
left = left + width + sep;


width = fontsize*1.33*5;
handles.edit_time_multiplier = uicontrol(panel_camera_distortion,'Style','edit',...
    'units','pixels','FontSize',fontsize,'Position',[left sep width height]);
handles.edit_time_multiplier.String = mat2str(params.picamera_time_multiplier);
handles.edit_time_multiplier.Callback = @edit_camera_distortion_callback;
uicontrol(panel_camera_distortion,'Style','text','String','Time mult.',...
    'units','pixels','FontSize',fontsize,'Position',[left 2*sep+height width height]);
left = left + width + sep; %#ok<NASGU>




% Panel with neurotar rotation
if params.nt_show_rotation_trace
    handles.panel_neurotar_rotation = subplot('Position',[0.05 0.1 0.25 0.1]);
    hold on
    handles.rotation_xaxis = line([0 max_time],[0 0],'Color' ,0.7*[1 1 1]);
    handles.rotation_yaxis = line([0 0],[-1 1],'Color' ,0.7*[1 1 1]);
    disableDefaultInteractivity(handle(handles.panel_neurotar_rotation))
    handles.rotation_trace = line(0,0,'Color',[0 0 0]);
    ylabel('\Delta\theta');
    ylim(handles.panel_neurotar_rotation,[-360 360]);
    set(handles.panel_neurotar_rotation,'ButtonDownFcn',@click_on_timeline);
end

% Panel with neurotar object distance
if params.nt_show_distance_trace
    handles.panel_neurotar_distance = subplot('Position',[0.70 0.25 0.25 0.1]);
    hold on
    handles.distance_xaxis = line([0 max_time],[0 0],'Color' ,0.7*[1 1 1]);
    handles.distance_yaxis = line([0 0],[-1 1],'Color' ,0.7*[1 1 1]);
    disableDefaultInteractivity(handle(handles.panel_neurotar_distance))
    %handles.distance_trace = plot(0,0,'-k');
    handles.distance_trace = line(0,0,'Color',[0 0 0]);
    set(handles.panel_neurotar_distance.XAxis,'visible','off')
    ylabel('Distance');
    ylim(handles.panel_neurotar_distance,[0 300]);
end

% Panel with neurotar arena
handles.panel_arena = subplot('Position',[0.33 0.08 0.33 0.2]);
hold(handles.panel_arena,'on');
disableDefaultInteractivity(handle(handles.panel_arena))
viscircles(handles.panel_arena,[0 0],params.arena_radius_mm,'Color',[0 0 0]);
if params.nt_show_leave_wall_boundary
    viscircles(handles.panel_arena,[0 0],params.arena_radius_mm-params.nt_max_distance_to_wall,'Color',[0 0 0 0.5]);

end
%hold('on');
handles.arena_trace = line(handles.panel_arena,0,0,'Color',[0 0 0]);
handles.arena_mouse = line(handles.panel_arena,0,0,'Color',[1 0 0],'LineWidth',2);
handles.arena_object = cell(9,1); % objects 1-9

%handles.arena_object = plot(panel_arena,NaN,NaN,'x','Color',[0 1 0],'MarkerSize',8);
%hold('off');
xlim([-params.arena_radius_mm params.arena_radius_mm]);
ylim([-params.arena_radius_mm params.arena_radius_mm]);
axis square off;
set(gca,'xtick',[])
set(gca,'ytick',[])
box off

if params.neurotar
    handles.overhead_neurotar_headring = plot(handles.panel_video(2),0,0,'o','color',[0 1 0]);
    update_neurotar_headring(handles.overhead_neurotar_headring,params);
    handles.overhead_neurotar_center = plot(handles.panel_video(2),0,0,'o','color',[1 1 0]);
    update_neurotar_center(handles.overhead_neurotar_center,params);
end

% draw arena on overhead image
handles.theta = linspace(0,2*pi,30);
x = 0 + params.arena_radius_mm * sin(handles.theta) ;
y = 0 + params.arena_radius_mm * cos(handles.theta) ;
[x,y] = nt_change_neurotar_to_overhead_coordinates(x,y,params);
handles.overhead_arena = line(handle(handles.panel_video(2)),x,y,'Color',[1 0 0]);
handles.overhead_neurotar_frame = line(handle(handles.panel_video(2)),0,0,'Color',[1 1 1]);
% update_neurotar_frame(handles.overhead_neurotar_frame,params);

handles.overhead_object = cell(9,1); % objects 1-9
xlim(handles.panel_video(2),[0 params.overhead_camera_width]);
ylim(handles.panel_video(2),[0 params.overhead_camera_height]);


if params.nt_show_help
    handles.fig_main_help = show_help(params);
else
    handles.fig_main_help = [];
end

nt_check_markers(record,params); % to give information about marker consistency

% set(handles.fig_main,'WindowKeyPressFcn',@keypressfcn);
% set(handles.fig_main,'UserData',struct('action',''));
% set(handles.fig_main,'CloseRequestFcn',@closerequestfcn);
end



function callback_toolbar(src,~)
% callback for toolbar buttons
toolbar = src.Parent;
fig = get(toolbar,'Parent');
userdata = get(fig,'UserData');
userdata.action = src.Tag;
set(fig,'UserData',userdata)
end
