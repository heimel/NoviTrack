function [ethogram,t,motifs,handle] = nt_get_ethogram(record,show)
%nt_get_ethogram. Gets ethogram from marker list
%
%  [ethogram,t,motifs,handle] = nt_get_ethogram(record,show)
%
% 2025, Alexander Heimel

if nargin<2 || isempty(show)
    show = true;
end

ethogram = [];
t = [];
motifs = [];

if ~isfield(record,'measures') || ~isfield(record.measures,'markers') || isempty(record.measures.markers)
    logmsg(['No markers found in record ' recordfilter(record)])
    return
end

params = nt_default_parameters(record);

motifs = params.markers(find([params.markers.behavior]));
motif_list = [motifs.marker]; 
n_motifs = length(motifs);

if n_motifs==0 % no behaviors
    return 
end

dt = 0.1; % 
if isfield(record.measures,'min_time')
    min_time = record.measures.min_time;
else
    min_time = floor(min([record.measures.markers.time])/60)*60;
end
if isfield(record.measures,'max_time')
    max_time = record.measures.max_time;
else
    max_time = ceil(max([record.measures.markers.time])/60)*60;
end

% min_time = 120;
% max_time = 300;

   
    n_samples = ceil((max_time-min_time)/dt);
ethogram = zeros(n_samples,n_motifs);

markers = record.measures.markers;
current_motif = [];
ind_start = [];
for i = 1:length(markers)
    marker = markers(i);
    if contains(motif_list,marker.marker(1))
        if ~isempty(current_motif)
            ind_stop = ceil((marker.time-min_time+0.0001)/dt);
            ind_stop = min(ind_stop,n_samples);
            ethogram(ind_start:ind_stop,current_motif) = current_motif;
        end       
        current_motif = find(motif_list==marker.marker(1));
        ind_start = ceil((marker.time-min_time+0.0001)/dt);
        ind_start = max(1,ind_start);
    end
end
if ~isempty(current_motif)
    ind_stop = n_samples;
    ethogram(ind_start:ind_stop,current_motif) = current_motif;
end
t = ((1:n_samples)-0.5)*dt + min_time;

%seq = max(ethogram,[],2);
%trans_motifs = zeros(n_motifs,n_motifs);
% for i=2:length(seq)
%     trans_motifs(seq(i-1),seq(i)) = trans_motifs(seq(i-1),seq(i)) + 1;
% end

if show && any(ethogram(:))
    figure('Name','Ethogram','NumberTitle','off')
    handle = axes();
    image('xdata', t,'ydata',1:n_motifs,'cdata',ethogram'+1);
    ylim([0.5,n_motifs+0.5]);
    xlim([min_time max_time]);
    set(gca,'ytick',1:n_motifs)
    set(gca,'yticklabel',cellfun(@(x) capitalize(x),{motifs.description},'UniformOutput',false));
    colormap([1 1 1; reshape([motifs.color],3,n_motifs)'])
    xlabel('Time (s)')
end
