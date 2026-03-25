% make_luminance_figs
%
% 2025, Alexander Heimel


load('C:\Users\heimel.HERSENINSTITUUT\OneDrive\Projects\Ren\Innate_approach\Data_collection\23.35.05\nttestdb_23.35.05_alexander_20250402.mat');

DARK = 1;
DIM = 2;
BRIGHT = 3;

ind_dark = find_record(db,'condition=dark');
ind_dim = find_record(db,'condition=dim');
ind_bright = find_record(db,'condition=bright');

%% Session speed mean (travelled distance)

session_speed_mean = {};
session_speed_mean{DARK} = ...
    arrayfun(@(rec) rec.measures.session_speed_mean,db(ind_dark));
session_speed_mean{DIM} = ...
    arrayfun(@(rec) rec.measures.session_speed_mean,db(ind_dim));
session_speed_mean{BRIGHT} = ...
    arrayfun(@(rec) rec.measures.session_speed_mean,db(ind_bright));

ivt_graph(session_speed_mean,[],...
    'ylab','Session mean speed (mm/s)',...
    'xticklabels',{'Dark','Dim','Bright'},'test','ranksum')

%% 

field = 'frac_in_center';
val = {};
val{DARK} = ...
    arrayfun(@(rec) rec.measures.(field),db(ind_dark));
val{DIM} = ...
    arrayfun(@(rec) rec.measures.(field),db(ind_dim));
val{BRIGHT} = ...
    arrayfun(@(rec) rec.measures.(field),db(ind_bright));

ivt_graph(val,[],...
    'ylab',field,...
    'xticklabels',{'Dark','Dim','Bright'},'test','ranksum')

