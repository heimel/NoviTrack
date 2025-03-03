function newud = nt_track_behavior_callback( ud)
%nt_track_behavior_callback. Helper function to start track from experimentdb
%
%   NEWUD = nt_track_behavior_callback( UD)
%
% 2023, Alexander Heimel

newud = ud;
newud.db(ud.current_record) = nt_track_behavior(ud.db(ud.current_record));
