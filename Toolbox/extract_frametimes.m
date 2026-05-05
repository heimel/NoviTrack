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
frametimes = NaN(n_frames,1);
if abs(n_frames/framerate-duration)<1E-3 
    % assume fixed framerate
    frametimes = (0:(n_frames-1))'/framerate;
else
    logmsg('Possible variable framerate. Retrieving frametimes for individual frames. This will be slow.')
    if ~isa(vid,'VideoReader')
        vid = VideoReader([vid.filename vid.ext]);
        %framerate = vid.FrameRate;
        n_frames = vid.NumFrames;
        %duration = vid.Duration;
        frametimes = NaN(n_frames,1);
    end

    curtime = vid.CurrentTime;
    vid.CurrentTime = 0;
    i = 1;
    frametimes(i) = vid.CurrentTime;
    h = waitbar(0,'Reading frame times');
    while vid.hasFrame
        if mod(i,300)==0
            waitbar(i/n_frames,h);
        end
        vid.readFrame();
        i = i + 1;
        frametimes(i) = vid.CurrentTime;
    end
    close(h)
    vid.CurrentTime = curtime;
end
