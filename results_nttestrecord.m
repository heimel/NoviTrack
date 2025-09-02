function results_nttestrecord( record )
%results_nttestrecord Shows results of neurotar experiment
%
% results_nttestrecord( RECORD )
%
% 2023, Alexander Heimel

%%
global measures global_record %#ok<GVMIS>
global_record = record;
evalin('base','global measures');
evalin('base','global analysed_script');
evalin('base','global global_record');

params = nt_default_parameters(record);

measures = record.measures;

if isempty(measures) 
    logmsg('No measures. Run analysis first');
    return
end

if isfield(measures,'markers' )
    nt_list_markers(measures);
end

nt_get_ethogram(record,true); % Show ethogram

nt_plot_photometry(record);

if ~isfield(measures,'behaviors')
    logmsg('No behaviors. Run analysis first');
    return
end

if ~isempty(measures.object_positions) && sum(measures.object_positions(:,4)==1 & ~isnan(measures.object_positions(:,2)))>0
    real_object_present = true;
else
    real_object_present = false;
end

%% Raw data
if params.nt_result_shows_individual_object_insertions
    nt_data = nt_load_neurotar_data(record);
    if isempty(nt_data)
        nt_data = nt_load_mouse_tracks(record);
    end

    if params.neurotar
        nt_data = nt_add_objects_to_nt_data( record, nt_data );
        for i = 1:length(measures.markers)
            switch measures.markers(i).marker
                case {'o','v','h'}
                    nt_plot_interaction(record,i,nt_data,params);
            end
        end % object insertion i
    end
end

%% Session summary
if isfield(measures,'session_fraction_running_forward')
    figure('Name','Session summary','NumberTitle','off');
    % Record comment
    subplot('position',[0.05 0.95 0.9 0.05]);
    text(0,0.5,subst_ctlchars([recordfilter(record) ',comment=' record.comment ]))
    axis off

    subplot(2,4,1)
    bar(measures.session_fraction_running_forward *100);
    ylabel('Running forward (% of time)')
    box off
    ylim([0 40]);
    h = gca;
    h.XAxis.Visible = 'off';

    subplot(2,4,2)
    bar(measures.session_start_running_forward_per_min);
    ylabel('Running forward (#/min)')
    box off
    ylim([0 70]);
    h = gca;
    h.XAxis.Visible = 'off';

    subplot(2,4,3)
    bar(measures.session_fraction_moving_backward *100);
    ylabel('Moving backward (% of time)')
    box off
    ylim([0 5]);
    h = gca;
    h.XAxis.Visible = 'off';

    subplot(2,4,4 )
    bar(measures.session_start_moving_backward_per_min);
    ylabel('Moving backward (#/min)')
    box off
    ylim([0 20]);
    h = gca;
    h.XAxis.Visible = 'off';
end

%% Peri-object time rates
if isfield(measures,'object_positions') && ~isempty(measures.object_positions)
    figure('Name','Peri-object time','NumberTitle','off')

    % Record comment
    subplot('position',[0.05 0.95 0.9 0.05]);
    text(0,0.5,subst_ctlchars([recordfilter(record) ',comment=' record.comment ]))
    axis off

    n_rates = length(params.nt_rates);
    for i=1:n_rates
        rate = params.nt_rates(i).rate;
        subplot(2,n_rates,i);
        hold on
        plot(measures.(rate).shuffles_time,measures.(rate).shuffles_mean,'-','color',[0.7 0.7 0.7]);
        plot(measures.(rate).time,measures.(rate).mean,'k-');
        plot(measures.(rate).time,measures.(rate).mean - measures.(rate).sem,'k--');
        plot(measures.(rate).time,measures.(rate).mean + measures.(rate).sem,'k--');
        xlabel('Time from object placement (s)');
        ylabel(params.nt_rates(i).description);
    end % rate i
end

%% Object interaction quantification
if isfield(measures,'object_positions') && ~isempty(measures.object_positions)
    figure('Name','Object interaction','NumberTitle','off');
    % Record comment
    subplot('position',[0.05 0.95 0.9 0.05]);
    text(0,0.5,subst_ctlchars([recordfilter(record) ',comment=' record.comment ]))
    axis off

    clr = [0.8 0.8 0];


    quantities = {'count_in_interaction_period','fraction_in_interaction_period'};
    for q = 1:length(quantities)
        quantity = quantities{q};

        subplot(1,length(quantities)+1,q);
        hold on
        num_behaviors = length(params.nt_behaviors);
        y = NaN(1,num_behaviors);
        for b = 1:num_behaviors
            behavior = params.nt_behaviors(b).behavior;
            shuffles = measures.(behavior).(['shuffles_' quantity]);
            hshuf = plot( b + [-0.5 0.5],nanmean(shuffles)*[1 1],'-','color',[0.7 0.7 0.7],'linewidth',2);
            plot( b + [-0.5 0.5],(nanmean(shuffles) - nansem(shuffles))*[1 1],'-','color',[0.7 0.7 0.7]);
            plot( b + [-0.5 0.5],(nanmean(shuffles) + nansem(shuffles))*[1 1],'-','color',[0.7 0.7 0.7]);
            y(b) = measures.(behavior).(quantity);
            [~,p] = ttest2(shuffles , measures.(behavior).(quantity));
            logmsg([behavior ' ' quantity ', p = ' num2str(p,2)]);
            plot_significance(b,b,max([y(b) mean(shuffles,'omitnan')]),p,[],[],true);
        end % b
        htrue = bar(1:num_behaviors,y,0.5,'facealpha',0.5,'facecolor',clr);
        set(gca,'XTick',1:num_behaviors);
        set(gca,'Xticklabel',{params.nt_behaviors(:).description});
        lab = capitalize(quantity);
        lab(lab=='_') = ' ';
        ylabel(lab);
        legend([htrue,hshuf],'Data','Shuffled','fontsize',8,'location','northoutside')
        legend boxoff
    end % quantity q

    subplot(1,length(quantities)+1,length(quantities)+1);
    hold on
    y = [];
    for i=1:length(params.nt_indices)
        index = params.nt_indices(i).index;
        y(i) = measures.(index).val;


        shuffles = measures.(index).shuffles;
        hshuf = plot( i + [-0.5 0.5],mean(shuffles,'omitnan')*[1 1],'-','color',[0.7 0.7 0.7],'linewidth',2);
        plot( i + [-0.5 0.5],(mean(shuffles,'omitnan') - nansem(shuffles))*[1 1],'-','color',[0.7 0.7 0.7]);
        plot( i + [-0.5 0.5],(mean(shuffles,'omitnan') + nansem(shuffles))*[1 1],'-','color',[0.7 0.7 0.7]);

        [~,p] = ttest2(shuffles , measures.(index).val);
        logmsg([index  ', p = ' num2str(p,2)]);
        plot_significance(i,i,max([y(i) mean(shuffles,'omitnan')]),p,[],[],true);
    end
    htrue = bar(1:length(params.nt_indices),y,0.5,'facealpha',0.5,'facecolor',clr);
    set(gca,'xtick',1:length(params.nt_indices));
    set(gca,'Xticklabel',{params.nt_indices(:).description});
    legend([htrue,hshuf],'Data','Shuffled','fontsize',8,'location','northoutside')
    legend boxoff
    ylim([0 1])

end

%%

logmsg('Measures available in workspace as ''measures'', record as ''global_record''.');