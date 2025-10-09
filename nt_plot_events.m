function nt_plot_events(record)
%nt_plot_events. Plots per event type all observables
%
%    nt_plot_events(RECORD)
%
% 2025, Alexander Heimel

measures = record.measures;

if ~isfield(measures,'event') || isempty(measures.event)
    return
end

params = nt_default_parameters(record);

event_types = string(fields(measures.event));

filename = fullfile(nt_session_path(record),'nt_snippets.mat');
load(filename,'snippets'); 
events = table([measures.markers.time]',string({measures.markers.marker}'),'VariableNames',{'time','event'});
n_events = height(events);


for event_type = event_types(:)'
    event = measures.event.(event_type);

    figure('Name',event_type,'NumberTitle','off')

    observables = string(fields(event));
    n_observables = length(observables);

    n_rows = ceil(sqrt(n_observables));
    n_cols = min(2,ceil(n_observables/n_rows)); % min. 2nd col for info

    n_actual_rows = n_rows*2+n_rows-1;
    n_actual_cols = n_cols+n_cols-1;

    tiledlayout(n_actual_rows,n_actual_cols,'TileSpacing','none','Padding','compact')

    nexttile(2)
    hold on
    xlim([0 1]);
    ylim([0 1]);

    txt = [' ' subst_ctlchars(record.sessionid) '\newline'];

    ind = strfind([params.markers.marker],event_type{1}(1));
    txt = [txt ' ' params.markers(ind).description ' ' event_type{1} ];

    text(0,0,txt);
    axis off


    count = 1;
    h = [];
    for observable = observables(:)'
        %subplot(n_rows,n_cols,count);
        row = ceil(count/n_cols)-1; % row starts at 0
        col = count - n_cols*row -1 ; % col starts at 0

        t = measures.snippets_tbins;

        %subplot(n_rows*2,n_cols,row*2*n_cols + col);
        nexttile(3*row*n_actual_cols + col*2+1);
        title([char(subst_ctlchars(observable)) ', n = ' num2str(event.(observable).n)])
        ind_events = find(events.event==event_type);
        imagesc('xdata',t,'cdata',snippets.data.(observable)(ind_events,:))
        xlabel([]);
        xticks([]);
        ylabel('Trial');
        if ~isempty(ind_events)
            ylim([1-0.5 length(ind_events)+0.5])
            yticks(unique([1 length(ind_events)]));
        end
        % subplot(n_rows*2,n_cols,row*2*n_cols + col + n_cols);
%        nexttile((1+row)*n_actual_cols + col );
        nexttile((3*row+1)*n_actual_cols + col*2+1);
        hold on

        plot([-params.nt_photometry_pretime params.nt_photometry_posttime],[0 0],'-k');
        box off
        y = event.(observable).snippet_mean;
        b = event.(observable).snippet_sem;
        switch observable
            otherwise 
                clr = [0 0 0];
        end
        errorband(t,y,1.97*b,clr,0.3); % 95% CI
        h(end+1) = plot(t,y,'Color',clr);
        xlabel('Time (s)')
        ylabel(snippets.unit.(observable));
        count = count + 1;
    end % observable 
end % event

