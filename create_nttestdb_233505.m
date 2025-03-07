function db = create_nttestdb_233505()
%create_nttestdb_233505. Creates testdb for 23.35.05 dataset
%
% 2025, Alexander Heimel

load('nttestdb_empty.mat','db');

record = db(1);
record.dataset = '23.35.05';
record.project = 'Innate_approach';
record.investigator = 'Zhiting Ren';
record.setup = 'behavior_arena';
record.comment = '';
record.measures = [];

projectfolder = 'W:\Ren\Innate_approach\Data_collection\23.35.05';

% Example file name: 108327_20241204_01_dim_firstAndNovelObject_overhead.h264

dir_mice = dir(projectfolder);
dir_mice(~[dir_mice(:).isdir]) = [];
count = 1;
for i=1:length(dir_mice)
    record.subject = dir_mice(i).name;
    if isnan(str2double(record.subject))
        continue % no mouse number
    end
    mouse_folder = fullfile(projectfolder,record.subject);
    dir_sessions = dir(mouse_folder);
    for j=1:length(dir_sessions)
        record.sessionid = dir_sessions(j).name;
        ind = find(record.sessionid=='_');
        if isempty(ind)
            continue
        end
        if length(ind)==2
            tempdate = record.sessionid( ind(1)+1:ind(2)-1);
        else
            tempdate = record.sessionid( ind(1)+1:end);
        end
        record.date = [tempdate(1:4) '-' tempdate(5:6) '-'  tempdate(7:8)];
        if length(ind)==2
            record.sessnr = str2double( record.sessionid(ind(end)+1:end));
        else
            record.sessnr = 1;
        end
        
        session_folder = fullfile(mouse_folder,record.sessionid);
        dir_tests = dir(fullfile(session_folder,'*overhead.h264'));
        if isempty(dir_tests)
            logmsg(['Could find *overhead.h264 for ' recordfilter(record) '. Check filenames.'])
            continue
        end

        for k=1:length(dir_tests)
            ind = find(dir_tests(k).name=='_');
            if length(ind)~=5
                continue
            end
            record.condition = dir_tests(k).name(ind(3)+1:ind(4)-1);
            record.stimulus =  dir_tests(k).name(ind(4)+1:ind(5)-1);
            db(count) = record;
            count = count + 1;

        end % k
    end
end