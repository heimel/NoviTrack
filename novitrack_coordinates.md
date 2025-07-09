# NoviTrack coordinates

2025, Alexander Heimel

Four distinct spatial coordinate systems are used in NoviTrack.

- Camera
- Overhead
- Arena
- Neurotar

Use Arena coordinates if there is no reason to use another coordinate system.

Two temporal coordinate systems are used in NoviTrack.

- Neurotar
- Video

The tracking defaults to using Neurotar time if it is available.

## Spatial coordinate systems 

### Overhead 

[overhead_x, overhead_y] (pxl) are coordinates on the image of the overhead camera. 
First coordinate is contained in (1:image_width), the second coordinate in (1:image_height).

### Camera 

[camera_x, camera_y] (mm) are real world coordinates centered at camera
center. x is along image width, with the same increasing direction.
Only used internally as intermediate transformation.

### Arena 

[arena_x, arena_y] (mm) are coordinates in the arena. 

On the neurotar setup, a physical object in the arena will have fixed arena coordinates. 
The neurotar coordinates of the object will change if the arena is moved on the neurotar setup. 

(0,0) is the center of the arena. 

For a fixed arena (not neurotar), params.overhead_arena_center is 2D vector with the location of 
this center of the arena in overhead image coordinates.

### Neurotar 

[neurotar_x, neurotar_y] (mm) are real world coordinates centered at
middle of neurotar setup, x is along bridge, y is orthogonal to
bridge, positive y is in front of the mouse. Neurotar coordinates should 
only be used on the Neurotar Mobile Homecage setup.

### Changing between coordinate frames 

To convert spatial coordinate frames:

```
[overhead_x, overhead_y] = change_neurotar_to_overhead_coordinates(neurotar_x,neurotar_y,measures,params)
[neurotar_x, neurotar_y] = change_overhead_to_neurotar_coordinates(overhead_x,overhead_y,measures,params);
[arena_x, arena_y] = change_neurotar_to_arena_coordinates(neurotar_x,neurotar_y)
[neurotar_x, neurotar_y] = change_arena_to_neurotar_coordinates(arena_x,arena_y)
```

and more. 

## Temporal coordinate systems

Each acquisition system, e.g. video, fiber photometry or neurotar, has its own clock in which their signals are 
stored. They are synchronized by shared triggers, of which the times are recorded in the clock of receiver.

### Some common configurations

- On the Neurotar setup, the video recordings starts first. The neurotar sends a trigger at the start of the recording. It does not record its own trigger, but it takes place at its time 0.

- For fiber photometry experiments, multiple triggers are manually send to the video raspberry pi's and the fiber photometer. The master time is from the video.


### Video 

NoviTrack is assuming that videos have a fixed framerate. The first frame will be at time 0 s, and the last at (video.NumFrames-1) * 1 / video.FrameRate


To convert temporal coordinate frames:
```
[to,offset,multiplier] = nt_change_times(from,triggers_from,triggers_to,multiplier_from,multiplier_to)
```

