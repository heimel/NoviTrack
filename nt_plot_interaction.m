function nt_plot_interaction(record,i,neurotar_data,params)
%nt_plot_interaction. Shows neurotar behavior during interaction period
%
%   nt_plot_interaction(RECORD,I,NEUROTAR_DATA,PARAMS)
%
% 2023, Alexander Heimel

measures = record.measures;

figure('Name',num2str( measures.markers(i).time,'%.1f'),'NumberTitle','off')
ind_extraction = find_record(measures.markers(i:end),'marker=t');
if ~isempty(ind_extraction)
    ind_extraction = i + ind_extraction - 1;
    time_extraction = measures.markers(ind_extraction).time;
else
    time_extraction = -inf;
end

n_rows = 2;
n_cols = 4;

time_start = measures.markers(i).time;
time_pre = time_start - 3;
time_stop = time_start + params.nt_interaction_period;
ind_full = find(neurotar_data.Time>=time_pre & neurotar_data.Time<=time_stop);
ind_start = ind_full( find(neurotar_data.Time(ind_full)>=time_start,1));


% Record comment
subplot('position',[0.05 0.95 0.9 0.05]);
text(0,0.5,[subst_ctlchars(  recordfilter(record)) ', comment=' record.comment ', marker ' measures.markers(i).marker])
axis off

ax_num = 1;

% Angular velocity towards object vs Forward speed
ax = subplot(n_rows,n_cols,ax_num);
ax_num = ax_num + 1;
hold on
plot(neurotar_data.Forward_speed(ind_full),neurotar_data.Angular_velocity_towards_object(ind_full))
xlim([-100 300]);
ylim([-300 300])
plot(xlim,params.nt_min_angular_velocity*[1 1],'--k');
plot(-params.nt_max_stationarity_speed*[1 1],ylim,'--k');
plot(params.nt_max_stationarity_speed*[1 1],ylim,'--k');
xlabel('Forward speed')
ylabel('Ang. vel. towards')

% Forward speed vs Time
ax = subplot(n_rows,n_cols,ax_num);
ax_num = ax_num + 1;
hold on
plot(neurotar_data.Time(ind_full),neurotar_data.Forward_speed(ind_full))
plot(xlim,params.nt_min_approach_speed*[1 1],'--k');
ylabel('Forward speed')
ylim([-100 300])
nt_show_markers(measures.markers,ax,params);
nt_show_behaviors(measures.behaviors,ax);

% Object distance derivative vs Time
if 0
    ax = subplot(n_rows,n_cols,ax_num);
ax_num = ax_num + 1;
    hold on
    plot(neurotar_data.Time(ind_full),neurotar_data.Object_distance_derivative(ind_full))
    plot(xlim,params.nt_min_approach_speed*[1 1],'--k');
    plot(xlim,params.nt_min_retreat_speed*[1 1],'--k');
    ylabel('Approach speed')
    ylim([-300 300])
    nt_show_markers(measures.markers,ax,params);
    nt_show_behaviors(measures.behaviors,ax);
end

% Angular velocity vs Time
ax = subplot(n_rows,n_cols,ax_num);
ax_num = ax_num + 1;

hold on
plot(neurotar_data.Time(ind_full),neurotar_data.Angular_velocity(ind_full))
plot(xlim,params.nt_min_angular_velocity*[1 1],'--k');
ylabel('Ang. vel.')
ylim([-250 250])
nt_show_markers(measures.markers,ax,params);
nt_show_behaviors(measures.behaviors,ax);

% Angular velocity towards object vs Time
ax = subplot(n_rows,n_cols,ax_num);
ax_num = ax_num + 1;
hold on
plot(neurotar_data.Time(ind_full),neurotar_data.Angular_velocity_towards_object(ind_full))
plot(xlim,params.nt_min_angular_velocity*[1 1],'--k');
ylabel('Ang. vel. towards')
ylim([-250 250])
nt_show_markers(measures.markers,ax,params);
nt_show_behaviors(measures.behaviors,ax);

% Object distance vs Time
if 0
    ax = subplot(n_rows,n_cols,ax_num);
    ax_num = ax_num + 1;

    hold on
    plot(neurotar_data.Time(ind_full),neurotar_data.Object_distance(ind_full))
    plot(xlim,params.nt_max_touching_distance*[1 1],'--k');
    ylabel('Object distance')
    ylim([0 300])
    nt_show_markers(measures.markers,ax,params);
    nt_show_behaviors(measures.behaviors,ax);
end

% Distance to wall vs Time
ax = subplot(n_rows,n_cols,ax_num);
ax_num = ax_num + 1;
hold on
plot(neurotar_data.Time(ind_full),neurotar_data.Distance_to_wall(ind_full))
plot(xlim,params.nt_max_distance_to_wall*[1 1],'--k');
ylabel('Distance to wall')
ylim([0 params.arena_radius_mm])
nt_show_markers(measures.markers,ax,params);
nt_show_behaviors(measures.behaviors,ax);

% Position in arena
ax = subplot(n_rows,n_cols,ax_num);
ax_num = ax_num + 1;
hold on
plot(neurotar_data.X(ind_full),neurotar_data.Y(ind_full))
ind_m = find_record(params.markers,['marker=' measures.markers(i).marker]);
if ~isempty(ind_m)
    color = params.markers(ind_m).color;
else
    color = [0 1 0];
end

indind = find(abs(neurotar_data.Forward_speed(ind_full))<params.nt_max_stationarity_speed);
plot(neurotar_data.X(ind_full(indind)),neurotar_data.Y(ind_full(indind)),'k.'); % stationary periods

plot(neurotar_data.X(ind_start),neurotar_data.Y(ind_start),'o','MarkerFaceColor',color,'MarkerEdgeColor',color)
xlim([-150 150]);
ylim([-150 150])
xlabel('X')
ylabel('Y')
viscircles([0 0],params.arena_radius_mm-params.nt_max_distance_to_wall,'Color',[0 0 0],'LineStyle','--');

viscircles([0 0],params.arena_radius_mm ,'Color',[0 0 0]);

axis square
axis off
text(0,-params.arena_radius_mm*1.1,'Mouse','HorizontalAlignment','center');


%Object position in Neurotar coordinates
ax = subplot(n_rows,n_cols,ax_num);
ax_num = ax_num + 1;
hold on
i = find(~isnan(neurotar_data.Object_X_neurotar(ind_full)),1);
plot(neurotar_data.Object_X_neurotar(ind_full(i)),neurotar_data.Object_Y_neurotar(ind_full(i)),'x')
plot(neurotar_data.Object_X_neurotar(ind_full),neurotar_data.Object_Y_neurotar(ind_full))
xlim([-params.neurotar_halfwidth_mm params.neurotar_halfwidth_mm]);
ylim([-params.neurotar_halfwidth_mm params.neurotar_halfwidth_mm]);
rectangle('position',[-params.neurotar_halfwidth_mm -params.neurotar_halfwidth_mm 2*params.neurotar_halfwidth_mm 2*params.neurotar_halfwidth_mm])
axis off
plot(0,0,'^k')
text(0,-params.neurotar_halfwidth_mm*1.1,'Object','HorizontalAlignment','center');
