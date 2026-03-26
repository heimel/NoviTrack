function [json, session_path] = nt_create_session()
%nt_create_session. Creates folder and fyd json log 
%
%  [JSON, SESSIONPATH] = nt_create_session()
%
%      Ask for session details in interaction with FYD database.
%      Upon close, an acqReady file is created in
%      params.root_communication_path/SETUP with the session path.
%
%    For Raspberry Pi video recording, use cli_picam_slave.py SETUP on
%    the pi. 
%
% 2023-2025, Alexander Heimel


params = nt_default_parameters();

json = myGetFYD();
if isempty(json)
    logmsg('Failed to get session data. Quitting.');
    return
end
[json, session_path] = create_session_folder( json, params );
savejson('', json, fullfile(session_path,[json.sessionid '_session.json']));


% Communicate
communication_path = fullfile(params.root_communication_path,json.setup);
if ~exist(communication_path,'dir')
    errormsg(['Folder ' communication_path ' does not yet exist. Check setup name and params.root_communication_path in processparams_local.m or create folder first. Not writing acqready.'],false);
    return
end

acqready_filename = fullfile(communication_path,'acqReady');
[fid,message] = fopen(acqready_filename,'wt');
if fid == -1
    errormsg(['Cannot write acqReady ' acqready_filename '. ' message])
end
fprintf(fid,'pathSpec\n%s\n',session_path);
fclose(fid);
logmsg(['Wrote sessionpath in ' acqready_filename ]);

end


function  [json, sessionpath] = create_session_folder( json, params )
% Create session folder and increase session number if necessary
new_folder = false;
existing_folder = false;
while ~new_folder
    json.sessionid = [json.subject '_' json.date(json.date~='-') '_' sprintf('%03d', json.sessnr)];
    sessionpath = nt_session_path(json,params);

    if ~exist(sessionpath, 'dir')
        if ~params.nt_debug
            mkdir(sessionpath);
            if existing_folder
                logmsg(['Original session folder existed. Increased session number to ' num2str(json.sessnr)]);
            end
            logmsg(sprintf('Created %s', sessionpath));
        end
        new_folder = true;
    else % folder exists, so increase session number
        existing_folder = true;
        json.sessnr = json.sessnr + 1;
    end
end
end

