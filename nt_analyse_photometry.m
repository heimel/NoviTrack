function [record,photometry,snippets] = nt_analyse_photometry(record,nt_data,verbose)
%nt_analyse_photometry. Analyse fiber photometry signal time locked to markers
%
%   [RECORD,PHOTOMETRY,SNIPPETS] = nt_analyse_photometry(RECORD,[NT_DATA],[VERBOSE=true])
%
%     Check 
%
% 2025, Alexander Heimel

if nargin<2 || isempty(nt_data)
    nt_data = [];
end
if nargin<3 || isempty(verbose)
    verbose = true;
end

if isempty(record.measures)
    logmsg('No data in measures. Track first.');
    return
end

snippets = [];
params = nt_default_parameters( record );

[photometry,measures] = nt_load_photometry(record,params);

if isempty(photometry)
    return
end

[photometry,measures] = nt_preprocess_photometry(photometry,measures,params);

record.measures = measures;

filename = fullfile(nt_photometry_folder(record),'nt_photometry.mat');
save(filename,'photometry');


if isempty(nt_data)
    return
end

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
