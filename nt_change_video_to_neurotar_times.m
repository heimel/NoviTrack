function neurotar_t = nt_change_video_to_neurotar_times( video_t, trigger_times, params)
% nt_change_video_to_neurotar_times. Change from video to neurotar time
%
% 2025, Alexander Heimel

neurotar_t = (video_t - trigger_times(1)) / params.picamera_time_multiplier;
