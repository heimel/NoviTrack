function stats = compute_stats_per_frame(filename,save_stats)
% compute_stats_per_frame. Computes mean and other stats for each video frame
%
%  STATS = compute_stats_per_frame( FILENAME, SAVE_RESULTS=true )
%     STATS.mean_luminance = n_frames x 1 of mean per frame
%     STATS.diff = n_frames x 1 of summed abs pixel difference.
%
%    if SAVE_RESULTS, then store STATS in [FILENAME_without_extenstion '_stats.mat']
%
% 2025, Alexander Heimel
%

if nargin<2 || isempty(save_stats)
    save_stats = true;
end

stats = [];
if ~exist(filename,'file')
    logmsg([filename ' does not exist.'])
    return
end

vid = VideoReader(filename);
n_frames = vid.NumFrames;

stats.mean_luminance = NaN(n_frames,1);
stats.diff = NaN(n_frames,1);

frame = readFrame(vid);
stats.mean_luminance(1) = mean(frame(:));
hWaitbar = waitbar(0, 'Processing frames...');

update_interval = 100; % Update waitbar every 100 frames

i = 2;
while hasFrame(vid)
        prev_frame = frame;
        frame = readFrame(vid);
        stats.mean_luminance(i) = mean(frame(:));
        stats.diff(i) = sum(abs(frame(:)-prev_frame(:)));
        
        if mod(i, update_interval) == 0
            waitbar(i/n_frames, hWaitbar, sprintf('Processing frame %d of %d', i, n_frames));
        end
    i = i + 1;

end

close(hWaitbar);


if save_stats
    [filepath,name] = fileparts(filename);
    stats_filename = fullfile(filepath,[name '_stats.mat']);
    save(stats_filename,'stats');
end
