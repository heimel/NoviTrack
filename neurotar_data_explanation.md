# Neurotar Data format

Compiled by Alexander Heimel.

The data is a tdmsDatastore. It contains the following channels.

- Dmaps_index - xompression information?
- Histogram_running_bouts - ?
- Histogram_speed - counts of presence in speed bins
- Histogram_zones - counts of presence in predefined zones
- Live_Data - data with immediate processing where applicable
- Pp_Data - data processed with zero-phase filters, aligned with beginning of recording
- Raw_sensor_data - magnets' unprocessed Cartesian coordinates
- Run_stats - stats of Running_time, Distance_travelled, Average_speed 
- SC_info - empty?
- Software_parameters - string with coded information
- TS_info - empty?

## Raw_sensor_data

Frame_N, HW_Timestamp, SW_timestamp, X1_raw, Y1_raw, X2_raw, Y2_raw, TTL_inputs, TTL_outputs
Magnet 1 and 2 are on the arena Y-axis, M1 is 50 mm in front of the center, M2 is 50 mm behind
   [raw_alpha,~] = cart2pol(X2-X1,-Y2+Y1);
   raw_alpha = raw_alpha/pi*180 + 90;
   X = cos(alpha/180*pi).*(-X1) - sin(alpha/180*pi).*(-Y1+shift)
   Y = -50 + sin(alpha/180*pi).*(-X1) +cos(alpha/180*pi).*(-Y1+shift);

   X = cos(alpha/180*pi).*(-X2) - sin(alpha/180*pi).*(-Y2+shift)
   Y = 50 + sin(alpha/180*pi).*(-X2) +cos(alpha/180*pi).*(-Y2+shift);

with shift the snout-neurotar-center distance? 

## Pp_Data

Pp_Data contains the following fields:

- Frame_N    
- HW_timestamp - hardware time (tick, uint32) from the ECU'S internal time source 
- Frame_HW_time - hardware time interval? (ms, uint16), e.g. 10, 10, ...            
- SW_timestamp - software time, e.g. "2024-05-06 15:05:05.444340705", "2024-05-06 15:05:05.454500675", ...            
- Frame_SW_time - software time (s), e.g. 0.0058895, 0.0068264, ...
- Since_track_start - time (s)     0.26104, 0.2712, ...
- R - distance (mm) between the mouse to the cage center 
- phi - angle (deg) of the mouse relative to the cage center      
- alpha - angle (deg) between the mouse's longitudinal axis and the cage's Y-axis       
- X,Y - coordinates (mm) of the mouse relative to the cage center         
- theta - used for debugging     
- beta - used for debugging       
- w - angle (deg) between the tail-nose axis and the tangent of the wall?      
- Speed - speed (mm/s)    
- Zone - zone
- TTL_inputs, TTL_outputs - status of IO   
- Key - status of the directional keys (Up, Down, Left, or Right)

[X, Y] = pol2cart( (phi-90)/180*pi, R) 


# Example of loading in Matlab

tdmsdata = tdmsDatastore([neurotar_filename '.tdms']);
tdmsdata.SelectedChannelGroup = "Pp_Data";
neurotar_data = readall(tdmsdata);
neurotar_data = neurotar_data{1};
