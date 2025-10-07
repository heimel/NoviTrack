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

for event_type = event_types(:)'
    event = measures.event.(event_type);

    figure('Name',event_type,'NumberTitle','off')
    subplot('position',[0.1 0.01 0.8 0.05]);
    text(0,0,recordfilter(record));
    axis off

    observables = string(fields(event));
    n_observables = length(observables);

    n_rows = ceil(sqrt(n_observables));
    n_cols = ceil(n_observables/n_rows);
    count = 1;
    h = [];
    for observable = observables(:)'
        subplot(n_rows,n_cols,count);
        plot([-params.nt_photometry_pretime params.nt_photometry_posttime],[0 0],'-k');
        hold on
        t = measures.snippets_tbins;
        y = event.(observable).snippet_mean;
        b = event.(observable).snippet_sem;
        switch observable
            otherwise 
                clr = [0 0 0];
        end
        errorband(t,y,b,clr,0.3);
        h(end+1) = plot(t,y,'Color',clr);
        title([char(subst_ctlchars(observable)) ', n = ' num2str(event.(observable).n)])
        xlabel('Time (s)')
        count = count + 1;
    end % observable 
end % event

