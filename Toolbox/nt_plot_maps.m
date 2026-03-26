function nt_plot_maps(record)
%nt_plot_maps. Plots photometry maps
%
%   nt_plot_maps( RECORD )
%
% 2025, Alexander Heimel

measures = record.measures;
if isempty(measures) || ~isfield(measures,'maps') || isempty(measures.maps)
    return
end

figure('Name','Maps','NumberTitle','off')

nexttile()
imagesc(measures.maps.counts')
axis image
set(gca,'ydir','normal')
set(gca,'xdir','reverse')
title('Presence')

axis off

for c = 1:length(measures.channels)
    channel = measures.channels(c);
    for t = 1:length(channel.lights)
        type = channel.lights(t).type;
        nexttile();
        imagesc(measures.maps.(channel.channel).(type)');
        axis image
        set(gca,'ydir','normal')
        set(gca,'xdir','reverse')

        axis off
        title(sprintf('%s - %s', channel.channel, type));
    end
end