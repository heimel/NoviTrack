function [record,photometry,snippets] = nt_analyse_photometry(record,nt_data,verbose)
%nt_analyse_photometry. Analyse fiber photometry signal time locked to markers
%
%   [RECORD,PHOTOMETRY,SNIPPETS] = nt_analyse_photometry(RECORD,[NT_DATA],[VERBOSE=true])
%
% 2025, Alexander Heimel

if nargin<2 || isempty(nt_data)
    nt_data = [];
end
if nargin<3 || isempty(verbose)
    verbose = true;
end

if isempty(record.measures)
    logmsg('No trigger_times in measures. Run Track first.');
    return
end

% Temporary. Can go when all data is updated.
if isfield(record.measures,'trigger_times') && iscell(record.measures.trigger_times)
    logmsg('Old format of trigger_times (before 2025-06-28). Re-open track first.')
    return
end

params = nt_default_parameters( record );

[photometry,measures] = nt_load_photometry(record,params);

[photometry,measures] = nt_preprocess_photometry(photometry,measures,params);

[snippets,measures] = nt_make_photometry_snippets(photometry,measures,params);

measures = nt_compute_photometry_measures(snippets,measures,params);

filename = fullfile(nt_photometry_folder(record),'nt_photometry.mat');
save(filename,'photometry','snippets');
logmsg(['Saved photometry analysis in ' filename]);

record.measures = measures;

if isempty(nt_data)
    return
end



%%
% figure 
% hold on
% plot(photometry.Channel1.gda3m.time,zscore(photometry.Channel1.gda3m.signal),'Color',[0 0.6 0]);
% plot(nt_data.Time,(nt_data.Speed-mean(nt_data.Speed,'omitnan'))/std(nt_data.Speed,'omitnan'),'Color',[0 0 0.6]);
% xlim(measures.period_of_interest)

%% Compute correlations
nt_data_sample_rate = 1/median(diff(nt_data.Time));

variables = {'Speed','Angular_velocity'};

measures.correlation = [];
for v = 1:length(variables)
    variable = variables{v};
    for c = 1:length(measures.channels)
        channel = measures.channels(c);
        photometry_sample_rate = measures.channels(c).sample_rate;
        resample_motion = (photometry_sample_rate < nt_data_sample_rate);
        for i =1:length(channel.lights)
            type = channel.lights(i).type;
            if resample_motion
                t = photometry.(channel.channel).(type).time;
                mask = (t>measures.period_of_interest(1) & t<measures.period_of_interest(2));
                x = photometry.Channel1.gda3m.signal(mask);
                y = interp1(nt_data.Time,nt_data.(variable),t(mask));
            else % resample photometry
                t = nt_data.Time;
                mask = (t>measures.period_of_interest(1) & t<measures.period_of_interest(2));
                x = nt_data.(variable)(mask);
                y = interp1(photometry.(channel.channel).(type).time,photometry.(channel.channel).(type).signal,t(mask));
            end
            [cc,p] = corrcoef(x,y);
            if p<0.05
                measures.correlation.(channel.channel).(type).(variable) = cc(1,2);
            end
        end % type i
    end % channel c
end % variable v

record.measures = measures;
