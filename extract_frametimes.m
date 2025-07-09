function frametimes = extract_frametimes(vid)
%extract_frametimes. Extract frametimes from video file
%
%  FRAMETIMES = extract_frametimes(VID)
%
%       VID can be a filename or an open video object.
%       Assumes a fixed frame rate.
%       Use ffpmeg -i vid and check if line with XX fps, YY tbr, ZZ tbn.
%       They should be identical. 
%
% 2025, Alexander Heimel

if ischar(vid)
    filename = vid;
    vid = VideoReader(filename);
end
framerate = vid.FrameRate;
n_frames = vid.NumFrames;
duration = vid.Duration;
frametimes = NaN(1,n_frames);
if abs(n_frames/framerate-duration)<1E-4 || fast
    % assume fixed framerate
    frametimes = (0:(n_frames-1))/framerate;
else
    logmsg('Possible variable framerate. Retrieving frametimes for individual frames. This will be slow.')
    curtime = vid.CurrentTime;
    vid.CurrentTime = 0;
    i = 1;
    frametimes(i) = vid.CurrentTime;
    while vid.hasFrame
        vid.readFrame();
        i = i + 1;
        frametimes(i) = vid.CurrentTime;
    end
    vid.CurrentTime = curtime;
end
