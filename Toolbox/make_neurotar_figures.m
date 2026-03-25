%MAKE_NEUROTAR_FIGURES
%
% Should be in Innate_approach\Data_analysis
%
% 2023, Alexander Heimel

%% Load database
%sParams = vr_defaultParameters();
sParams = nt_default_parameters(); % perhaps should be line above?
dbfilename = fullfile(sParams.strOutputPath,'Innate_approach','Data_analysis','db_nt_94755.mat');
%dbfilename = fullfile(sParams.strOutputPath,'Innate_approach','Data_analysis','db_nt_test_alexander.mat');
load(dbfilename,'db');
logmsg(['Loaded database ' dbfilename]);
db = sort_db(db);
return

%% Get subjects from FYD
% USING DATAJOINT
% You must have a tables definition folder in your path with the name of the database such as: +heimellab
% import credentials from your parameter file

dbpar = nhi_fyd_CSFparms(); %#ok<*UNRCH>
setenv('DJ_HOST', dbpar.Server)
setenv('DJ_USER', dbpar.User)
setenv('DJ_PASS', dbpar.Passw)
Database = dbpar.Database;  %= yourlab
Con = dj.conn(); %check the connection
if ~Con.isConnected
    logmsg('Could not connect to FYD');
end
subjects_tupel = heimellab.ProjectsSubjects & 'project="Innate_approach"';
%subjects_struct = fetch(subjects_tupel) % use fetch(subjects_tupel,'subjectidx') to add subjectidx field
%subjects = {subjects_struct.subject};
selected_subjects = fetch(subjects_tupel, 'subject')

% Example for one subject
% fetch(heimellab.Subjects & 'subjectid=83731','sex')
subjects = fetch(heimellab.Subjects & rename_field(selected_subjects,'subject','subjectid'),'genotype','sex','birthdate','shortdescr')


%% compare headbar angle, without matching
% head bar angle was changed on 2023-08-01

db = db(arrayfun(@(x) ~isempty(x.measures),db));
ind = find_record(db,'subject!exampleVideo,subject!testLight');
db = db(ind);

db_00deg = db(find_record(db,'date<2023-08-01'));
db_30deg = db(find_record(db,'date>2023-07-31'));

figure
flds = {'session_start_running_forward_per_min','session_fraction_running_forward','session_start_moving_backward_per_min','session_fraction_moving_backward'}
flds = {'session_forward_speed_max','session_forward_speed_std'};
for i = 1:length(flds)
    h = subplot(1,length(flds),i)
    fld = flds{i};
    y00 = cellfun(@(x) x.(fld),{db_00deg.measures});
    y30 = cellfun(@(x) x.(fld),{db_30deg.measures});
    ivt_graph({y00,y30},[],'style','bar','errorbars','sem','xticklabels',{'0 deg','30 deg'},'ylab',subst_ctlchars(fld),'axishandle',h);
end
%exportgraphics(gcf,'neurotar_headring_angle_all_data.pdf')

%% compare headbar angle, with matching
subjects = unique({db_30deg.subject})
n_subjects = length(subjects);
clear db_00deg_select db_30deg_select
for i = 1:n_subjects
    subject = subjects{i};
    ind = find_record(db_00deg,['subject=' subject]);
    db_00deg_select(i) = db_00deg(ind(end));
    ind = find_record(db_30deg,['subject=' subject]);
    db_30deg_select(i) = db_30deg(ind(end));
end
figure
flds = {'session_start_running_forward_per_min','session_fraction_running_forward','session_start_moving_backward_per_min','session_fraction_moving_backward'}

flds = {'session_forward_speed_max','session_forward_speed_std'};
for i = 1:length(flds)
    h = subplot(1,length(flds),i)
    fld = flds{i};
    y00 = cellfun(@(x) x.(fld),{db_00deg_select.measures});
    y30 = cellfun(@(x) x.(fld),{db_30deg_select.measures});
    ivt_graph({y00,y30},[],'style','bar','errorbars','sem','xticklabels',{'0 deg','30 deg'},'ylab',subst_ctlchars(fld),'axishandle',h,'showpairing',1);
end
%exportgraphics(gcf,'neurotar_headring_angle_matched_data.pdf')


%% Compare laser behaviors
subjects = {'82793','82794','85230','85231','85232','85233'};
clr = [0.8 0.8 0];
params = nt_default_parameters();
for b = 1:length(params.nt_behaviors)
    behavior = params.nt_behaviors(b).behavior;
    for s = 1:length(subjects)
        ind = find_record(db,['comment=*laser*,subject=' subjects{s}]);
        for d = 1:2
            count_in_interaction_period.(behavior){d}(s)  = db(ind(d)).measures.(behavior).count_in_interaction_period;
            shuffles_count_in_interaction_period.(behavior){d}(s)  = mean(db(ind(d)).measures.(behavior).shuffles_count_in_interaction_period);

            fraction_in_interaction_period.(behavior){d}(s)  = db(ind(d)).measures.(behavior).fraction_in_interaction_period;
            shuffles_fraction_in_interaction_period.(behavior){d}(s)  = mean(db(ind(d)).measures.(behavior).shuffles_fraction_in_interaction_period);
        end % d
    end % s
    figure('Name',params.nt_behaviors(b).description,'NumberTitle','off')
    h = subplot(2,2,1);
    ivt_graph(count_in_interaction_period.(behavior),[],'style','bar',...
        'errorbars','sem','showpairing',true,'ylab',['Count ' params.nt_behaviors(b).description],'axishandle',h,'xticklabels',{'Session 1','Session 2'});
    ivt_graph(shuffles_count_in_interaction_period.(behavior),[],'style','level',...
        'errorbars','sem','extra_options','errorbars_sides,both','showpoints',0,'ylab',['Count ' params.nt_behaviors(b).description],'axishandle',h,'xticklabels',{'Session 1','Session 2'});


    h = subplot(2,2,2);
    ivt_graph(fraction_in_interaction_period.(behavior),[],'style','bar','errorbars','sem','showpairing',true,'ylab',['Fraction ' params.nt_behaviors(b).description],'axishandle',h,'xticklabels',{'Session 1','Session 2'});
    ivt_graph(shuffles_fraction_in_interaction_period.(behavior),[],'style','level',...
        'errorbars','sem','extra_options','errorbars_sides,both','showpoints',0,'ylab',['Fraction ' params.nt_behaviors(b).description],'axishandle',h,'xticklabels',{'Session 1','Session 2'});

    % look for animal consistency
    std_true = std(count_in_interaction_period.(behavior){2} - count_in_interaction_period.(behavior){1});
    n_shuffles = 50;
    std_shuffles = nan(1,n_shuffles);
    for s = 1:n_shuffles
        std_shuffles(s) = std(count_in_interaction_period.(behavior){2}(randperm(length(count_in_interaction_period.(behavior){2}))) - count_in_interaction_period.(behavior){1});
    end
    subplot(2,2,3)
    hold on
    histogram(std_shuffles,10);
    plot(std_true*[1 1],ylim)
    [h,p] = ttest2(std_shuffles,std_true);
    logmsg(['Animal consistentcy ' behavior ' p = ' num2str(p,2)]);
    yl = ylim;
    plot_significance(std_true,std_true,yl(2)*0.9,p)

    % look for animal consistency
    std_true = std(fraction_in_interaction_period.(behavior){2} - fraction_in_interaction_period.(behavior){1});
    n_shuffles = 50;
    std_shuffles = nan(1,n_shuffles);
    for s = 1:n_shuffles
        std_shuffles(s) = std(fraction_in_interaction_period.(behavior){2}(randperm(length(fraction_in_interaction_period.(behavior){2}))) - fraction_in_interaction_period.(behavior){1});
    end
    subplot(2,2,4)
    hold on
    histogram(std_shuffles,10);
    plot(std_true*[1 1],ylim)
    [h,p] = ttest2(std_shuffles,std_true);
    logmsg(['Animal consistentcy ' behavior ' p = ' num2str(p,2)]);
    yl = ylim;
    plot_significance(std_true,std_true,yl(2)*0.9,p)
end % b

%% Compare laser indices
subjects = {'82793','82794','85230','85231','85232','85233'};
clr = [0.8 0.8 0];
params = nt_default_parameters();
val = [];
shuffles = [];
for b = 1:length(params.nt_indices)
    index = params.nt_indices(b).index
    for s = 1:length(subjects)
        ind = find_record(db,['comment=*laser*,subject=' subjects{s}])
        for d = 1:2
            val.(index){d}(s)  = db(ind(d)).measures.(index).val;
            shuffles.(index){d}(s)  = mean(db(ind(d)).measures.(index).shuffles);
        end % d
    end % s
    figure('Name',params.nt_indices(b).description,'NumberTitle','off')
    h = subplot(2,2,1);
    ivt_graph(val.(index),[],'style','bar',...
        'errorbars','sem','showpairing',true,'ylab',['Count ' params.nt_indices(b).description],'axishandle',h,'xticklabels',{'Session 1','Session 2'});
    ivt_graph(shuffles.(index),[],'style','level',...
        'errorbars','sem','extra_options','errorbars_sides,both','showpoints',0,'ylab',['Count ' params.nt_indices(b).description],'axishandle',h,'xticklabels',{'Session 1','Session 2'});

    % look for animal consistency
    std_true = std(val.(index){2} - val.(index){1})
    n_shuffles = 50;
    std_shuffles = nan(1,n_shuffles);
    for s = 1:n_shuffles
        std_shuffles(s) = std(val.(index){2}(randperm(length(val.(index){2}))) - val.(index){1})
    end
    subplot(2,2,2)
    hold on
    histogram(std_shuffles,10);
    plot(std_true*[1 1],ylim)
end % b

%% Compare turn towards laser vs control

ind = find_record(db,'comment=*laser*');
db_laser = db(ind);
ind = find_record(db,'comment=*control*');
db_control = db(ind);
disp('subject,laser,control')
behavior = 'turn_towards';
val_laser = NaN(length(db_laser),1);
val_control = NaN(length(db_laser),1);
for i=1:length(db_laser)
    if ~isfield(db_laser(i).measures,behavior)
        continue
    end



    val_laser(i) = db_laser(i).measures.(behavior).count_in_interaction_period;
    ind = find_record(db_control,['subject=' db_laser(i).subject ',date=' db_laser(i).date ]);
    if isempty(ind)
        val_control(i) = NaN;
    else
        val_control(i) = db_control(ind).measures.(behavior).count_in_interaction_period;
    end
    disp([db_laser(i).subject ', ' num2str(val_laser(i),2) ', ' num2str(val_control(i),2)])
end
ivt_graph({val_laser(~isnan(val_control)),val_control(~isnan(val_control))},...
    [],'errorbars','sem','showpairing',1,'ylab','Orienting #','xticklabels',{'Laser','Control runs'})
[p,h]=signrank(val_laser,val_control);
logmsg(['Difference between laser and control, p = ' num2str(p,2)])
exportgraphics(gcf,fullfile(getdesktopfolder,'orienting_laser_vs_control.pdf'))

% params.nt_min_angular_velocity = 100; % deg/s
% params.nt_max_stationarity_speed = 20; % mm/s
% params.nt_interaction_period = 10; % s, period to count interactions
% p = 0.03, sign-rank
% turn_towards: 82793: 6; 85230: 4; 85231: 3;  85233: 4; 82794: 1; 85232: 0;

%% Compare turn away laser vs control
ind = find_record(db,'comment=*laser*,comment!*freely*');
db_laser = db(ind);
ind = find_record(db,'comment=*control*,comment!*freely*');
db_control = db(ind);
disp('subject,laser,control')
behavior = 'turn_away';
val_laser = NaN(length(db_laser),1);
val_control = NaN(length(db_laser),1);
for i=1:length(db_laser)
    if ~isfield(db_laser(i).measures,behavior)
        continue
    end
    val_laser(i) = db_laser(i).measures.(behavior).count_in_interaction_period;
    ind = find_record(db_control,['subject=' db_laser(i).subject ',date=' db_laser(i).date ]);
    if isempty(ind)
        val_control(i) = NaN;
    else
        val_control(i) = db_control(ind).measures.(behavior).count_in_interaction_period;
    end
    disp([db_laser(i).subject ', ' num2str(val_laser(i),2) ', ' num2str(val_control(i),2)])
end
ivt_graph({val_laser(~isnan(val_control)),val_control(~isnan(val_control))},...
    [],'errorbars','sem','showpairing',1,'ylab','Turning away #','xticklabels',{'Laser','Control runs'})
[p,h]=signrank(val_laser,val_control);
logmsg(['Difference between laser and control, p = ' num2str(p,2)])


% params.nt_min_angular_velocity = 100; % deg/s
% params.nt_min_run_speed = 90; % mm/s
% params.nt_interaction_period = 10; % s, period to count interactions
% p = 0.078, sign-rank
% turn_away:    85233: 9; 85230: 4; 85231: 2;  82793: 1; 82974: 0; 85232: 0;
% turn_towards: 82793: 6; 85230: 4; 85231: 3;  85233: 4; 82794: 1; 85232: 0;

%% Compare leave wall laser vs control
ind = find_record(db,'comment=*laser*,comment!*freely*');
db_laser = db(ind);
ind = find_record(db,'comment=*control*,comment!*freely*');
db_control = db(ind);
disp('subject,laser,control')
behavior = 'leave_wall';
val_laser = NaN(length(db_laser),1);
val_control = NaN(length(db_laser),1);
for i=1:length(db_laser)
    if ~isfield(db_laser(i).measures,behavior)
        continue
    end
    if strcmp(db_laser(i).subject,'82794') && strcmp(db_laser(i).date,'2023-08-11')
        logmsg('Temporarily removing record because arena was not cleaned in between. Many feacal boli present');
        continue
    end
    quantity = 'count_in_interaction_period'; 
    %quantity = 'fraction_in_interaction_period';

    val_laser(i) = db_laser(i).measures.(behavior).(quantity);
    ind = find_record(db_control,['subject=' db_laser(i).subject ',date=' db_laser(i).date ]);
    if isempty(ind)
        val_control(i) = NaN;
    else
        val_control(i) = db_control(ind).measures.(behavior).(quantity);
    end
    disp([db_laser(i).subject ', ' num2str(val_laser(i),2) ', ' num2str(val_control(i),2)])
end
ivt_graph({val_laser(~isnan(val_control)),val_control(~isnan(val_control))},...
    [],'errorbars','sem','showpairing',1,'ylab','Leaving wall #','xticklabels',{'Laser','Control runs'});
[p,h]=signrank(val_laser,val_control);
logmsg(['Difference between laser and control, p = ' num2str(p,2)])


%% Habituation turn towards across sessions
ind = find_record(db,'comment=*laser*,comment!*freely*');
db_laser = sort_db(db(ind));
%behavior = 'turn_towards';
behavior = 'leave_wall';
subjects = unique({db_laser.subject});
n_subjects = length(subjects);
n_sessions = ceil(length(db_laser)/n_subjects);
n_sessions = 4;
disp('ONLY TAKING FIRST FOUR SESSIONS')
vals = NaN(n_subjects,n_sessions);
for s = 1:length(subjects)
    ind = find_record(db_laser,['subject=' subjects{s}]);
    disp(['subject=' subjects{s}])
    v = arrayfun(@(x) x.measures.(behavior).count_in_interaction_period,db_laser(ind));
    vals(s,1:4)  = [v(1:3) v(end)];
end
ivt_graph({vals(:,1),vals(:,2),vals(:,3),vals(:,4)},[],'showpairing',1,'errorbars','sem','ylab','Orienting #','xlab','Session')
exportgraphics(gcf,fullfile(getdesktopfolder,'orienting_over_sessions.pdf'))

%% Habituation turn towards across sessions
ind = find_record(db,'comment=*laser*');
db_laser = sort_db(db(ind));
behavior = 'run';
subjects = unique({db_laser.subject});
n_subjects = length(subjects);
n_sessions = ceil(length(db_laser)/n_subjects);
vals = NaN(n_subjects,n_sessions);
for s = 1:length(subjects)
    ind = find_record(db_laser,['subject=' subjects{s}]);
    vals(s,:)  = arrayfun(@(x) x.measures.(behavior).count_in_interaction_period,db_laser(ind))
end
ivt_graph({vals(:,1),vals(:,2),vals(:,3)},[],'showpairing',1,'errorbars','sem','ylab','Run in response #','xlab','Session')
exportgraphics(gcf,fullfile(getdesktopfolder,'runs_in_response_over_sessions.pdf'))

%% Habituation session run across sessions
ind = find_record(db,'comment=*laser*');
db_laser = sort_db(db(ind));
subjects = unique({db_laser.subject});
n_subjects = length(subjects);
n_sessions = ceil(length(db_laser)/n_subjects);
vals = NaN(n_subjects,n_sessions);
for s = 1:length(subjects)
    ind = find_record(db_laser,['subject=' subjects{s}]);
    vals(s,:)  = arrayfun(@(x) x.measures.session_count_start_running_forward,db_laser(ind))
end
ivt_graph({vals(:,1),vals(:,2),vals(:,3)},[],'showpairing',1,'errorbars','sem','ylab','# Run bouts per session','xlab','Session')
exportgraphics(gcf,fullfile(getdesktopfolder,'runs_per_sessions.pdf'))

%% Run in response compared to shuffle
ind = find_record(db,'comment=*laser*');
db_laser = sort_db(db(ind));
subjects = unique({db_laser.subject});
n_subjects = length(subjects);
vals = [];
for s = 1:length(subjects)
    ind = find_record(db_laser,['subject=' subjects{s}]);
    % take first session
    for i=1:length(ind)
        vals(end+1,1) = db_laser(ind(i)).measures.run.count_in_interaction_period;
        vals(end,2) = mean(db_laser(ind(i)).measures.run.shuffles_count_in_interaction_period);
    end
end
ivt_graph({vals(:,1),vals(:,2)},[],'showpairing',1,'errorbars','sem',...
    'ylab','# Runs in response','xticklabels',{'Data','Shuffled'},'xlab','\newlineAll sessions')
exportgraphics(gcf,fullfile(getdesktopfolder,'runs_response_vs_shuffled.pdf'))

%% Turn towards in response compared to shuffle
ind = find_record(db,'comment=*laser*');
db_laser = sort_db(db(ind));
subjects = unique({db_laser.subject});
n_subjects = length(subjects);
vals = [];
for s = 1:length(subjects)
    ind = find_record(db_laser,['subject=' subjects{s}]);
    for i = 1:length(ind)
        vals(end+1,1) = db_laser(ind(i)).measures.turn_towards.count_in_interaction_period;
        vals(end,2) = mean(db_laser(ind(i)).measures.turn_towards.shuffles_count_in_interaction_period);
    end
end
ivt_graph({vals(:,1),vals(:,2)},[],'showpairing',1,'errorbars','sem',...
    'ylab','# Orients in response','xticklabels',{'Data','Shuffled'},'xlab','\newlineAll sessions','spaced',1.5,'markers','open_circle')
exportgraphics(gcf,fullfile(getdesktopfolder,'orient_response_vs_shuffled.pdf'))


