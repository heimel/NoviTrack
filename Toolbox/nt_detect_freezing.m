function record = nt_detect_freezing(record,verbose)
%nt_detect_freezing. Detect freezing from mouse movement
%
%   record = nt_detect_freezing(record,verbose)
%
% 2025, Alexander Heimel

% Freezing detection
logmsg('Tracking completed. Detecting freezing')
freezePeriodNr = 0;
firstHit = 1;
hitnr = 0;

smoothVidDif = movmean(vidDif,2*params.wc_freeze_smoother);
deriv2 = diff(smoothVidDif);
minimalMovement = min(smoothVidDif);
nomotion = (smoothVidDif(1:end-1) < (minimalMovement + params.wc_difThreshold)) & (abs(deriv2) < params.wc_deriv2thres);

freezeTimes = [];
freeze_duration = [];
tailbase = [];
nose = [];
stim = [];
for i = 1:length(nomotion)
    if nomotion(i)
        if firstHit
            startFreezeTime = frametimes(i);
            firstHit = false;
            hitnr = 1;
        else
            hitnr = hitnr + 1;
        end
    else % motion again
        if hitnr/framerate > params.wc_freezeduration_threshold
            stopFreezeTime = frametimes(i-1);
            freezePeriodNr = freezePeriodNr + 1;
            freezeTimes(freezePeriodNr,1:2) = [startFreezeTime stopFreezeTime]; %#ok<AGROW>
            freeze_duration(freezePeriodNr) = stopFreezeTime-startFreezeTime; %#ok<AGROW>
            tailbase(freezePeriodNr,:) = record.measures.tailbase_trajectory(i,:); %#ok<AGROW>
            nose(freezePeriodNr,:) = record.measures.nose_trajectory(i,:); %#ok<AGROW>
            if isfield(record.measures,'stim_trajectory') && ~isempty(record.measures.stim_trajectory)
                stim(freezePeriodNr,:) = record.measures.stim_trajectory(i,:); %#ok<AGROW>
            else
                stim(freezePeriodNr,:) = [NaN NaN]; %#ok<AGROW>
            end
        end
        firstHit = true;
        hitnr = 0;
    end
end
% check if freezing was continuing
if hitnr/framerate > params.wc_freezeduration_threshold
    stopFreezeTime = frametimes(i-1);
    freezePeriodNr = freezePeriodNr + 1;
    freezeTimes(freezePeriodNr,1:2) = [startFreezeTime stopFreezeTime]; 
    freeze_duration(freezePeriodNr) = stopFreezeTime-startFreezeTime; 
    tailbase(freezePeriodNr,:) = record.measures.tailbase_trajectory(i,:); 
    nose(freezePeriodNr,:) = record.measures.nose_trajectory(i,:); 
    if isfield(record.measures,'stim_trajectory') && ~isempty(record.measures.stim_trajectory)
        stim(freezePeriodNr,:) = record.measures.stim_trajectory(i,:); 
    else
        stim(freezePeriodNr,:) = [NaN NaN]; 
    end
end

record.measures.freezetimes_aut = freezeTimes;
record.measures.freeze_duration_aut = freeze_duration;
record.measures.mousemove_aut = smoothVidDif;

if isempty(freezeTimes)
    logmsg('No freezing detected');
end
logmsg('Freeze detection complete');
