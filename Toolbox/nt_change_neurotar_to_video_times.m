function video_t = nt_change_neurotar_to_video_times( neurotar_t, trigger_times, params)
% nt_change_neurotar_to_video_times. Change from neurotar to video time
%
% 2025, Alexander Heimel

video_t = params.picamera_time_multiplier * neurotar_t + trigger_times(1);
