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
    record.measures = measures;
    return
end

[photometry,measures] = nt_preprocess_photometry(photometry,measures,params);

record.measures = measures;

filename = fullfile(nt_photometry_folder(record),'nt_photometry.mat');
save(filename,'photometry');

if isempty(nt_data)
    return
end

nt_data_sample_rate = 1/median(diff(nt_data.Time));

%% Compute map

ind = find(nt_data.Time >= measures.period_of_interest(1) & nt_data.Time <= measures.period_of_interest(2));
time = nt_data.Time(ind);


params.nt_map_bins = 100;
n_x = ceil(sqrt(params.nt_map_bins));
n_y = n_x;
range_x = [min(nt_data.CoM_X(ind)) max(nt_data.CoM_X(ind))];
range_y = [min(nt_data.CoM_Y(ind)) max(nt_data.CoM_Y(ind))];

res = min([diff(range_x)/n_x diff(range_y)/n_y]);
n_x = ceil(diff(range_x)/res);
n_y = ceil(diff(range_y)/res);

x = nt_data.CoM_X(ind) - range_x(1) ;
x = ceil(x/res);
x(x==0) = 1;
y = nt_data.CoM_Y(ind) - range_y(1) ;
y = ceil(y/res);
y(y==0) = 1;

counts = zeros(n_x,n_y);
for i = 1:length(x)
    counts(x(i),y(i)) = counts(x(i),y(i)) + 1;
end

measures.maps.counts = counts;
for c = 1:length(measures.channels)
    channel = measures.channels(c);
    for t = 1:length(channel.lights)
        type = channel.lights(t).type;
        map = NaN(n_x,n_y);
        ph = interp1(photometry.(channel.channel).(type).time,photometry.(channel.channel).(type).signal,time);
        for i = 1:length(time)
            if isnan(map(x(i),y(i)))
                map(x(i),y(i)) = ph(i);
            else
                map(x(i),y(i)) = map(x(i),y(i)) + ph(i);
            end
        end
        map = map ./ counts;
        measures.maps.(channel.channel).(type) = map;
    end % type t
end % channel c

%% Compute correlations

variables = {'Speed','Angular_velocity','Abs_angular_velocity','Distance_to_center'};

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
                x = photometry.(channel.channel).(type).signal(mask);
                y = interp1(nt_data.Time,nt_data.(variable),t(mask));
            else % resample photometry
                t = nt_data.Time;
                mask = (t>measures.period_of_interest(1) & t<measures.period_of_interest(2));
                x = nt_data.(variable)(mask);
                y = interp1(photometry.(channel.channel).(type).time,photometry.(channel.channel).(type).signal,t(mask));
            end
            [cc,p] = corrcoef(x,y,'Rows','complete');
            if p<0.10
                logmsg('Found some correlation')
                measures.correlation.(channel.channel).(type).(variable) = cc(1,2);
            end
        end % type i
    end % channel c
end % variable v

record.measures = measures;
