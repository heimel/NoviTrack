function nt_plot_photometry(record)
%nt_plot_photometry. Plots photometry results
%
%    nt_plot_photometry(record)
%
% 2025, Alexander

measures = record.measures;
params = nt_default_parameters(record);

filename = fullfile(nt_photometry_folder(record),'nt_photometry.mat');
if exist(filename,'file')
    load(filename,'photometry');
else
    return
end

filename = fullfile(nt_session_path(record),'nt_snippets.mat');
load(filename,'snippets'); 


%% Full time course + heatplot all snippets
for c = 1:length(measures.channels)
    channel = measures.channels(c);
    figure('Name',channel.channel,'NumberTitle','off');
    subplot('position',[0.1 0.01 0.8 0.05])
    text(0,0,recordfilter(record));
    axis off

    ax1 = subplot(2,1,1);
    hold on
    for i = 1:length(channel.lights)
        type = channel.lights(i).type;
        % if strcmp(type,'isosbestic') && measures.photometry_isosbestic_correction
        %     continue % don't plot if used for correction
        % end
        f_signal = photometry.(channel.channel).(type).signal;
        time = photometry.(channel.channel).(type).time;
        mask = (time>measures.period_of_interest(1) & time<measures.period_of_interest(2));
        clr = params.(['nt_color_' type]);
        plot(time(mask),f_signal(mask),'Color',clr);
    end
    ylabel('Fluorescence (a.u.)')
    xlabel('Time (s)')
    plot(measures.period_of_interest(1)*[1 1],ylim,'-k');
    plot(measures.period_of_interest(2)*[1 1],ylim,'-k');

    txt = string(subst_ctlchars(record.sessionid));
    txt = txt + " " + channel.channel;

    txt =txt +  ", " + channel.hemisphere + " " + channel.location;
    if ~isempty(channel.green_sensor)
        txt = txt + ", green = " +  channel.green_sensor;
    end
    if ~isempty(channel.red_sensor)
        txt =txt +  ", red = " + channel.red_sensor;
    end
    ind410 = find([channel.lights(:).wavelength]==410);
    ind470 = find([channel.lights(:).wavelength]==470);

    txt(end+1) = sprintf("Median410 = %.2f, Median470 = %.2f, Fit of green = %.2f x Isos %+.2f",...
        channel.lights(ind410).median,channel.lights(ind470).median,channel.fit_isos(1),-channel.fit_isos(2));
    title(txt)
    nt_show_markers(measures.markers,ax1,params,[],[])

    % Heat plot all snippets
    %    events = table([measures.markers.time]',string({measures.markers.marker}'),'VariableNames',{'time','event'});
        events = measures.events;

    n_plots = length(channel.lights);
    if measures.photometry_isosbestic_correction
        n_plots = n_plots - 1;
    end
    count = 1;
    for i = 1:length(channel.lights)
        type = channel.lights(i).type;
        if measures.photometry_isosbestic_correction && strcmp(type,'isosbestic')
            continue
        end
        subplot(2,n_plots,n_plots+count)
        hold on
        [~,ind] = sort(events.event);
        imagesc('XData',measures.snippets_tbins',...
            'CData',snippets.data.([channel.channel '_' type])(ind,:))
        ylim([0.5 height(events)+0.5])

        xlabel('Time (s)')
        ylabel('Event (sorted by type)')
        colorbar
        title(type)
        count = count + 1;
    end % i
end %c


% %% Traces per event type
% for c = 1:length(measures.channels)
%     channel = measures.channels(c);
%     figure('Name',channel.channel,'NumberTitle','off');
%     subplot('position',[0.1 0.01 0.8 0.05])
%     text(0,0,recordfilter(record));
%     axis off
% 
%     n_events = length(measures.unique_events);
%     n_rows = ceil(sqrt(n_events));
%     n_cols = ceil(n_events/n_rows);
%     count = 1;
%     for event = measures.unique_events(:)'
%         subplot(n_rows,n_cols,count);
%         plot([-params.nt_pretime params.nt_posttime],[0 0],'-k');
%         hold on
%         h = [];
%         labels = {};
%         for i = 1:length(channel.lights)        
%             type = channel.lights(i).type;
%             if measures.photometry_isosbestic_correction && strcmp(type,'isosbestic')
%                 continue
%             end
% 
%             clr = params.(['nt_color_' type]);
% 
%             t = measures.photometry_snippets_tbins;
%             y = measures.photometry.(event).(channel.channel).(type).snippet_mean;
%             b = measures.photometry.(event).(channel.channel).(type).snippet_sem;
%             errorband(t,y,b,clr,0.3);
%             h(end+1) = plot(t,y,'Color',clr);
%             labels{end+1} = type;
%         end % i
%         xlabel('Time (s)')
%         ylabel('Signal (z-score)')
%         ylim([-6 6])
%         title(event)
%         legend(h,labels);
%         legend boxoff
%         count = count + 1;
%     end
% 
% end


% fp = measures.fp;
% flds = setdiff(fields(fp),'t');
% for i = 1:length(flds)
%     field = flds{i};
%     channels = unique(setdiff(fields(fp.(field)),'n_events'));
%     n_channels = length(channels);
% 
%     for c = 1:n_channels
%         channel = channels{c};
%         figure('Name',[ field ' - ' channel],'NumberTitle','off')
% 
%         subplot('position',[0.1 0.01 0.8 0.05])
%         text(0,0,recordfilter(record));
%         axis off
% 
%         % df/f
%         subplot(2,2,1);
%         hold on
%         plot(fp.t,fp.(field).(channel).dfof,'Color',params.nt_color_gcamp)
%         if ~measures.applied_isosbestic_correction
%             plot(fp.t,fp.(field).(channel).dfof_isos,'Color',params.nt_color_isos)
%         end
%         ylabel('\DeltaF/F');
%         xlabel('Time (s)');
%         title([field ', ' channel ', n = ' num2str(fp.(field).n_events)])
% 
%         subplot(2,2,2);
%         hold on
%         plot(fp.t,fp.(field).(channel).zscore,'Color',params.nt_color_gcamp)
%         if ~measures.applied_isosbestic_correction
%             plot(fp.t,fp.(field).(channel).zscore_isos,'Color',params.nt_color_isos)
%         end
%         ylabel('z-score');
%         % plot(fp.t,...
%         %     (fp.(field).(channel).zscore)-(fp.(field).(channel).zscore_isos),'-','Color',[0 0.8 0]);
%         % ylabel('z-score (corr.)');
%         xlabel('Time (s)');
%         title([field ', ' channel ', n = ' num2str(fp.(field).n_events)])
% 
% 
%         f_signal = squeeze(single_events.fp.(field).(channel).peristimulus(2,:,:));
%         f_iso = squeeze(single_events.fp.(field).(channel).peristimulus(1,:,:));
%         X = [f_iso(:) ones(size(f_iso(:)))];
%         f_artifact = X * measures.fit_isos{1};
%         f_artifact = reshape(f_artifact,size(f_signal));
% 
%         subplot(4,2,5)
%         imagesc(f_signal,'xdata',single_events.fp.t_bins)
%         set(gca,'ydir','normal')
%         xlabel('Time (s)')
%         ylabel('Event')
%         title('Raw fluorescence')
% 
%         subplot(4,2,7)
%         plot(single_events.fp.t_bins, mean(f_signal))
%         xlabel('Time (s)')
%         ylabel('Event-averaged F')
% 
% 
%         subplot(4,2,6)
%         imagesc(f_signal-f_artifact,'xdata',single_events.fp.t_bins)
%         set(gca,'ydir','normal')
%         xlabel('Time (s)')
%         ylabel('Event')
%         title('Isosbestic corrected')
% 
%         subplot(4,2,8)
%         plot(single_events.fp.t_bins, mean(f_signal-f_artifact))
%         xlabel('Time (s)')
%         ylabel('Event-averaged F')
% 
% 
% 
% 
%     end % channel c
% end % field
