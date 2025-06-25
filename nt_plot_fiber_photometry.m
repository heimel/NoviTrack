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

fp = measures.fp;

flds = setdiff(fields(fp),'t');

for i = 1:length(flds)
    field = flds{i};
    channels = unique(setdiff(fields(fp.(field)),'n_trials'));
    n_channels = length(channels);

    figure('Name',field,'NumberTitle','off')
    for c = 1:n_channels
        channel = channels{c};
        subplot(n_channels,1,c);
        hold on
        % plot(fp.t,fp.(field).(channel).dfof,'g')
        % plot(fp.t,fp.(field).(channel).dfof_isos,'b')
        % ylabel('\DeltaF/F');

        % plot(fp.t,fp.(field).(channel).zscore,'g')
        % plot(fp.t,fp.(field).(channel).zscore_isos,'b')
% ylabel('z-score');

         plot(fp.t,...
             (fp.(field).(channel).zscore)-(fp.(field).(channel).zscore_isos),'-','Color',[0 0.8 0]);

 ylabel('z-score (corr.)');

        if c==n_channels
            xlabel('Time (s)');
        end
        if c==1
            title([field ', n = ' num2str(fp.(field).n_trials)])
        end
    end
end
