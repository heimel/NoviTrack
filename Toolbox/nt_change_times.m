function [to,offset,multiplier] = nt_change_times(from,triggers_from,triggers_to,multiplier_from,multiplier_to)
%nt_change_times. Changes times from one reference to another
%
%  [TO,OFFSET,MULTIPLIER] = nt_change_times(FROM,TRIGGERS_FROM,TRIGGERS_TO,[MULTIPLIER_FROM],[MULTIPLIER_TO])
%
%    FROM is vector with time stamps
%    TRIGGERS_FROM is vector of triggers with time stamps in FROM reference
%    frame.
%    TRIGGERS_TO is vector of triggers with time stamps in TO reference
%    frame.
%    MULTIPLIER_FROM is multiplier to divide data in FROM reference frame.
%    MULTIPLIER_TO is multiplier to divide data in TO reference frame.
%    The multipliers are only used if there is only a single trigger to
%    match the reference frames.
%
%   TO = MULTIPLIER * FROM + OFFSET
%
% 2025, Alexander Heimel

n_triggers_from = length(triggers_from);
n_triggers_to = length(triggers_to);

if n_triggers_from==1 && n_triggers_to>1
    logmsg('Detected too many triggers TO. Using only the first! May be wrong trigger. If so edit trigger log.')
    triggers_to = triggers_to(1);
    n_triggers_to = 1;
end
if n_triggers_to==1 && n_triggers_from>1
    logmsg('Detected too many triggers FROM. Using only the first! May be wrong trigger. If so edit trigger log.')
    triggers_from = triggers_from(1);
    n_triggers_from = 1;
end


% deal with missing triggers at start or end
if n_triggers_from > n_triggers_to
    % missing first triggers_from?
    cc = corrcoef(triggers_from(n_triggers_from-n_triggers_to+1:end),triggers_to);
    cc_missing_first = cc(1,2);

    % missing last triggers_from?
    cc = corrcoef(triggers_from(1:n_triggers_to),triggers_to);
    cc_missing_last = cc(1,2);

    if cc_missing_first>cc_missing_last
        triggers_from = triggers_from(n_triggers_from-n_triggers_to+1:end);
        n_triggers_from = length(triggers_from);
        logmsg('Missed first FROM triggers in TO reference');
    else
        triggers_from = triggers_from(1:n_triggers_to);
        n_triggers_from = length(triggers_from);
        logmsg('Missed last FROM triggers in TO reference');
    end
end


if n_triggers_from < n_triggers_to
    % missing first triggers_to?
    cc = corrcoef(triggers_from,triggers_to(n_triggers_to-n_triggers_from+1:end));
    cc_missing_first = cc(1,2);

    % missing last triggers_to?
    cc = corrcoef(triggers_from,triggers_to(1:n_triggers_from));
    cc_missing_last = cc(1,2);

    if cc_missing_first>cc_missing_last
        triggers_to = triggers_to(n_triggers_to-n_triggers_from+1:end);
        n_triggers_to = length(triggers_to);
        logmsg('Missed first TO triggers in FROM reference');
    else
        triggers_to = triggers_to(1:n_triggers_from);
        n_triggers_to = length(triggers_to);
        logmsg('Missed last TO triggers in FROM reference');
    end
end

if n_triggers_from == 1 % add second artificial trigger
    if ~exist('multiplier_from','var') || ~exist('multiplier_to','var')
        logmsg('Only single matching trigger and no multipliers given. Assuming them to be 1. This is inaccurate for large times.')
        multiplier_from = 1;
        multiplier_to = 1;
    end
    triggers_from(2,1) = triggers_from(1) + 1000 * multiplier_from;
    triggers_to(2,1) = triggers_to(1) + 1000 * multiplier_to;
end

cc = corrcoef(triggers_from,triggers_to);
cc = cc(1,2);
if cc<0.999
    logmsg(['Only correlation of ' num2str(cc,3) ' between TO and FROM triggers. This suggest missing triggers and inaccurate time change.'])
end

y = triggers_to;
x = [ones(length(triggers_from),1) triggers_from];
b1 = x\y;
offset = b1(1);
multiplier = b1(2);


to = from * multiplier + offset;
