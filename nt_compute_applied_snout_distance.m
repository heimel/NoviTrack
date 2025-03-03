function neurotar_snout_distance_mm = nt_compute_applied_snout_distance(record)
%nt_compute_applied_snout_distance. Computes from raw magnet data the shift applied by neurotar
%
%   neurotar_snout_distance_mm = nt_compute_applied_snout_distance(record)
%
% 2024, Alexander Heimel

params = nt_default_parameters(record);
neurotar_path = fullfile(params.networkpathbase,record.project,'Data_collection','Neurotar');
neurotar_mask = fullfile(neurotar_path,['Track_[' record.date '*]_' record.subject '_session' num2str(record.sessnr)]);
d = dir(neurotar_mask);
if isempty(d) && strcmp(record.subject,'exampleVideo')
    neurotar_path = fullfile(params.networkpathbase,record.project,'Data_collection','Neurotar','exampleVideos');
    neurotar_mask = fullfile(neurotar_path,['Track_[' record.date '*]_' record.subject '_session' num2str(record.sessnr)]);
    d = dir(neurotar_mask);
end

if isempty(d)
    errormsg(['Cannot find Neurotar data in ' neurotar_mask]);
    return
end
if length(d)>1
    errormsg(['Cannot decide which data to use. Two folders matching ' neurotar_mask]);
    return
end
neurotar_sessionname = d(1).name;

neurotar_filename = fullfile(neurotar_path, neurotar_sessionname, [neurotar_sessionname(1:find(neurotar_sessionname==']',1)) ]);


logmsg(['Loading neurotar data ' neurotar_filename '.tdms']);
tdmsdata = tdmsDatastore([neurotar_filename '.tdms']);
tdmsdata.SelectedChannelGroup = "Pp_Data";
neurotar_data = readall(tdmsdata);
neurotar_data = neurotar_data{1};

tdmsdata.SelectedChannelGroup = "Raw_sensor_data";
raw_data = readall(tdmsdata);
raw_data = raw_data{1};

%%
n = length(neurotar_data.X);
s = ceil(n/1000);
X = neurotar_data.X(1:s:n);
Y = neurotar_data.Y(1:s:n);
R = neurotar_data.R(1:s:n);
phi = neurotar_data.phi(1:s:n);
alpha = neurotar_data.alpha(1:s:n);

X1 = raw_data.X1_raw(1:s:n);
Y1 = raw_data.Y1_raw(1:s:n);
X2 = raw_data.X2_raw(1:s:n);
Y2 = raw_data.Y2_raw(1:s:n);

DX = X2-X1;
DY = Y2-Y1;

[raw_alpha,~] = cart2pol(DX,-DY);
raw_alpha = raw_alpha/pi*180 + 90; % equal to alpha


%% Simple fit X to X1 and Y1
g = @(x) cos(alpha/180*pi).*(-X1) - sin(alpha/180*pi).*(-Y1+x(1))  ;
shift_1X = fminsearch(@(x)  sum( (X- g(x)).^2 ),0);

cc = corrcoef(X,g(shift_1X));
if cc(1,2)<0.99
    logmsg('Poor fit')

    figure;
    plot(X,'k-')
    hold on
    plot( g(shift_1X),'r-')
end

%% Simple Fitting Y to X1 and Y1
g = @(x) -50+  sin(alpha/180*pi).*(-X1) +cos(alpha/180*pi).*(-Y1+x);
shift_1Y = fminsearch(@(x)  sum( (Y- g(x)).^2 ),0);
cc = corrcoef(Y,g(shift_1Y));
if cc(1,2)<0.99
    logmsg('Poor fit');
    figure;
    plot(Y,'k-')
    hold on
    plot( g(shift_1Y),'r-')
end
%% Simple fit X to X2 and Y2
g = @(x) cos(alpha/180*pi).*(-X2) - sin(alpha/180*pi).*(-Y2+x)  ;
shift_2X = fminsearch(@(x)  sum( (X- g(x)).^2 ),0);
cc = corrcoef(X,g(shift_2X));
if cc(1,2)<0.99
    logmsg('Poor fit');

    figure;
    plot(X,'k-')
    hold on
    plot( g(shift_2X),'r-')
end

%% Simple Fitting Y to X1 and Y1
g = @(x) 50 + sin(alpha/180*pi).*(-X2) +cos(alpha/180*pi).*(-Y2+x);
shift_2Y = fminsearch(@(x)  sum( (Y- g(x)).^2 ),0);
cc = corrcoef(Y,g(shift_2Y));
if cc(1,2)<0.99
    logmsg('Poor fit');
    figure;
    plot(Y,'k-')
    hold on
    plot( g(shift_2Y),'r-')
end


%%
shift = round(mean([shift_2X shift_1Y shift_2X shift_2Y]));
neurotar_snout_distance_mm = shift;
logmsg(['Snout distance: ' num2str(neurotar_snout_distance_mm) ' mm'])
if std([shift_2X shift_1Y shift_2X shift_2Y])>1
    logmsg('Discrepancy in calculated shifts. Check record ')


    fit_X = cos(alpha/180*pi).*(-X1) -sin(alpha/180*pi).*(-Y1+shift);
    fit_Y = -50 + sin(alpha/180*pi).*(-X1) +cos(alpha/180*pi).*(-Y1+shift);
    fit_X2 = cos(alpha/180*pi).*(-X2) -sin(alpha/180*pi).*(-Y2+shift);
    fit_Y2 = +50+ sin(alpha/180*pi).*(-X2) +cos(alpha/180*pi).*(-Y2+shift);
    figure
    hold on
    plot(X,Y);
    plot(fit_X,fit_Y)
    plot(fit_X2,fit_Y2)

end
