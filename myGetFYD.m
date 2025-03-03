function sJson = myGetFYD()
%myGetFYD is wrapper around getFYD
%
%  sJson = myGetFYD()
%
%  does not break if sql database cannot be accessed
%  returns last saved entry
%
%  2022, Alexander Heimel

sJson = [];

ret = which('getFYD');
if isempty(ret)
    logmsg('Cannot find getFYD. Make sure to clone FYD_Matlab repository and add to the Matlab path.');
    return
end

if ~canConnectFYD % failure
    logmsg('Cannot access FYD server. Trying to load last fyd record');
    load(fullfile(fileparts(which('getFYD')),'fydsaved.mat'),'fydsaved');
    sJson = fydsaved; 
    %sJson.lab = 'Heimellab';
    %sJson.project = 'Innate_approach';
    %sJson.dataset = '22.35.01';
    sJson.subject = 'test';
    %sJson.condition = '';
    %sJson.stimulus = 'mouseVR';
    sJson.setup = 'Neurotar';
    sJson.investigator = 'Zhiting Ren';
    sJson.date = datestr(now,'yyyy-mm-dd');
    %sJson.sessionid = [sJson.subject '_20240329_001'];
    %sJson.logfile = [sJson.sessionid '_log.m'];
    %sJson.sessnr = 1;
    %sJson.version = '1.0';
    %sJson.path = '';

    return
end
    
sJson = getFYD();
