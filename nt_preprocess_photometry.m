function [photometry,measures] = nt_preprocess_photometry(photometry,measures,params)
%nt_preprocess_photometry. Performs isosbestic correction and filtering of photometry data
%
%  [photometry,measures] = nt_preprocess_photometry(photometry,measures,params)
%
%  See nt_load_photometry for structure of photometry
%
% 2025, Alexander Heimel

if params.nt_photometry_isosbestic_correction
    for c = 1:length(measures.channels)
        channel = measures.channels(c);
        ind_isos = find(contains({channel.lights(:).type},'isosbestic'));
        ind_signal = setdiff(1:length(channel.lights),ind_isos); % assume only a single signal channel
        type = channel.lights(ind_signal).type;

        time = photometry.(channel.channel).(type).time;
        f_signal = photometry.(channel.channel).(type).signal;
        f_iso = interp1(photometry.(channel.channel).isosbestic.time,photometry.(channel.channel).isosbestic.signal,time,'spline','extrap');

        % for computing regression parameters only use period of interest
        mask = (time>=measures.period_of_interest(1) & time<=measures.period_of_interest(2));

        if params.nt_only_use_pretime_for_isosbestic_correction
            mask = false(size(time));
            for i = 1:length(measures.markers)
                mask = mask | (time>measures.markers(i).time-params.nt_pretime & time<measures.markers(i).time);
            end % i
            if sum(mask)/channel.sample_rate<10
                logmsg('Warning: less than 10s of pre-marker data to use for isosbestic correction');
            end
        end

        f_signal_part = f_signal(mask);
        f_iso_part = f_iso(mask);

        % Linear regression: F_signal ≈ a * F_iso + b
        X = [f_iso_part ones(size(f_iso_part))];
        measures.channels(c).fit_isos = X \ f_signal_part;  % Least-squares solution

        % use all data again to make correction
        X = [f_iso ones(size(f_iso))];
        f_artifact = X * measures.channels(c).fit_isos;

        photometry.(channel.channel).(type).signal = photometry.(channel.channel).(type).signal - f_artifact;
    end % c
end % isosbestic correction
measures.photometry_isosbestic_correction = params.nt_photometry_isosbestic_correction;

% filter
for c = 1:length(measures.channels)
    channel = measures.channels(c);
    for i =1:length(channel.lights)
        type = channel.lights(i).type;
        f_signal = photometry.(channel.channel).(type).signal;
        photometry.(channel.channel).(type).signal = filter_photometry(f_signal,channel.sample_rate,params);
    end
end

% time shift 
for c = 1:length(measures.channels)
    channel = measures.channels(c);
    photometry.(channel.channel).(type).time = photometry.(channel.channel).(type).time - params.nt_photometry_time_offset;
end



end


function y = filter_photometry(x, fs, params)
% x   : raw (or corrected) photometry vector
% fs  : sampling rate (Hz)

lp = params.nt_photometry_low_pass;
hp = params.nt_photometry_high_pass;
ord = params.nt_photometry_butterworth_order;

x = x(:);

% 1) Optional median filter to kill spikes (set window to 0 to skip)
medWin = round(params.nt_photometry_median_filter_window * fs);  
if medWin >= 3 && mod(medWin,2)==0
    medWin = medWin+1;
end
if medWin >= 3
    x = medfilt1(x, medWin, 'truncate');
end

% 2) High-pass (remove slow drift/bleach)
if hp > 0
    [bHP, aHP] = butter(ord, hp/(fs/2), 'high');
    x = filtfilt(bHP, aHP, x);
end

% 3) Low-pass (remove high-frequency noise)
if lp > 0 && lp < fs/2
    [bLP, aLP] = butter(ord, lp/(fs/2), 'low');
    y = filtfilt(bLP, aLP, x);
else
    y = x;
end

end

