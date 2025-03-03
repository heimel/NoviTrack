function res = canConnectFYD()
%canConnectFYD returns true if FYD server can be reached
%
%  res = canConnectFYD()
%
% 2022-2024, Alexander Heimel

fyd_server = 'fyd2.nin.nl'; % was nhi-fyd.nin.knaw.nl until March 2024
 
[ret,~]  = system(['ping -n 1 ' fyd_server]);
if ret==1 % failure
    logmsg(['Cannot access ' fyd_server '. Perhaps not on NIN intranet?']);
    res = false;
    return
end

res = true;