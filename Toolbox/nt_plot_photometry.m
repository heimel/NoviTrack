function nt_plot_photometry(record)
%nt_plot_photometry. Plots photometry results
%
%    nt_plot_photometry(record)
%
% 2025, Alexander

measures = record.measures;
params = nt_load_parameters(record);

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

    if ~isempty(snippets) && ~isempty(events)
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
    end
end %c

%% Correlation between channels (for now only green channels)
n_channels = length(measures.channels);
if n_channels>1 
    figure('Name','Channel correlation','NumberTitle','off');
end

count = 0;
for c1=1:n_channels
    channel1 = measures.channels(c1);

    for c2=1:(c1-1)
        count = count + 1;
        channel2 = measures.channels(c2);

        subplot(n_channels-1,n_channels-1,count);
        hold on
        x = zscore(photometry.(channel1.channel).green.signal);
        y = zscore(photometry.(channel2.channel).green.signal);
        plot(x,y,'.')
        xl = xlim();
        msk = (sqrt(x.^2 + y.^2)>2 & x>0 & y>0);
        lm  = fitlm(x(msk),y(msk));
        a = lm.Coefficients.Estimate(1);
        b = lm.Coefficients.Estimate(2);
        xf = linspace(xl(1),xl(2),100);
        yf = b*xf + a;
        mskf = (sqrt(xf.^2 + yf.^2)>2 & xf>0);
        %plot( xf(mskf),yf(mskf));
        plot(xlim(),[0 0],'-k');
        plot([0 0],ylim(),'-k');
        phi = linspace(0,2*pi,30);
        r = 2;
        plot(r*sin(phi),r*cos(phi),'-k');

        xyline
        axis equal
        xlabel([channel1.location ' - ' channel1.green_sensor ' (z)']);
        ylabel([channel2.location ' - ' channel2.green_sensor ' (z)']);

        cc = corrcoef(x,y);


        title([subst_ctlchars(record.sessionid) ' - r = ' num2str(cc(1,2))]);

    end
end
