function nt_plot_fiber_photometry(record)
%nt_plot_fiber_photometry. Plots fiber photometry results
%
%    nt_plot_fiber_photometry(record)
%
% 2025, Alexander

measures = record.measures;

if ~isfield(measures,'fp') || isempty(measures.fp)
    return
end

params = nt_default_parameters(record);

folder = nt_fiber_photometry_folder(record);
filename = fullfile(folder,'novitrack_fp.mat');
single_events = load(filename); % single event data



fp = measures.fp;
flds = setdiff(fields(fp),'t');
for i = 1:length(flds)
    field = flds{i};
    channels = unique(setdiff(fields(fp.(field)),'n_events'));
    n_channels = length(channels);

    for c = 1:n_channels
        channel = channels{c};
        figure('Name',[ field ' - ' channel],'NumberTitle','off')

        subplot('position',[0.1 0.01 0.8 0.05])
        text(0,0,recordfilter(record));
        axis off

        % df/f
        subplot(2,2,1);
        hold on
        plot(fp.t,fp.(field).(channel).dfof,'Color',params.nt_color_gcamp)
        if ~measures.applied_isosbestic_correction
            plot(fp.t,fp.(field).(channel).dfof_isos,'Color',params.nt_color_isos)
        end
        ylabel('\DeltaF/F');
        xlabel('Time (s)');
        title([field ', ' channel ', n = ' num2str(fp.(field).n_events)])

        subplot(2,2,2);
        hold on
        plot(fp.t,fp.(field).(channel).zscore,'Color',params.nt_color_gcamp)
        if ~measures.applied_isosbestic_correction
            plot(fp.t,fp.(field).(channel).zscore_isos,'Color',params.nt_color_isos)
        end
        ylabel('z-score');
        % plot(fp.t,...
        %     (fp.(field).(channel).zscore)-(fp.(field).(channel).zscore_isos),'-','Color',[0 0.8 0]);
        % ylabel('z-score (corr.)');
        xlabel('Time (s)');
        title([field ', ' channel ', n = ' num2str(fp.(field).n_events)])


        f_signal = squeeze(single_events.fp.(field).(channel).peristimulus(2,:,:));
        f_iso = squeeze(single_events.fp.(field).(channel).peristimulus(1,:,:));
        X = [f_iso(:) ones(size(f_iso(:)))];
        f_artifact = X * measures.fit_isos{1};
        f_artifact = reshape(f_artifact,size(f_signal));

        subplot(4,2,5)
        imagesc(f_signal,'xdata',single_events.fp.t_bins)
        set(gca,'ydir','normal')
        xlabel('Time (s)')
        ylabel('Event')
        title('Raw fluorescence')

        subplot(4,2,7)
        plot(single_events.fp.t_bins, mean(f_signal))
        xlabel('Time (s)')
        ylabel('Event-averaged F')


        subplot(4,2,6)
        imagesc(f_signal-f_artifact,'xdata',single_events.fp.t_bins)
        set(gca,'ydir','normal')
        xlabel('Time (s)')
        ylabel('Event')
        title('Isosbestic corrected')

        subplot(4,2,8)
        plot(single_events.fp.t_bins, mean(f_signal-f_artifact))
        xlabel('Time (s)')
        ylabel('Event-averaged F')




    end % channel c
end % field
