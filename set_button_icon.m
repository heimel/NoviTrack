function set_button_icon(button,arg)
%set_button_icon. Sets icon on button
%
%  set_button_icon(BUTTON,ARG)
% 
%      BUTTON is handle to button object
%      ARG is dependent on button type
%
% 2025, Alexander Heimel

tag = split(button.Tag,';');
args = tag(2:end);
tag = tag{1};

switch tag
    case 'marker_add'
        ico = create_icon(args{1},'Color',str2num(args{2}));
    case 'toggle_play'
        if arg
            ico = [
                1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 ;
                1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 ;
                1 1 1 0 0 0 1 1 1 1 0 0 0 1 1 1 ;
                1 1 1 0 0 0 1 1 1 1 0 0 0 1 1 1 ;
                1 1 1 0 0 0 1 1 1 1 0 0 0 1 1 1 ;
                1 1 1 0 0 0 1 1 1 1 0 0 0 1 1 1 ;
                1 1 1 0 0 0 1 1 1 1 0 0 0 1 1 1 ;
                1 1 1 0 0 0 1 1 1 1 0 0 0 1 1 1 ;
                1 1 1 0 0 0 1 1 1 1 0 0 0 1 1 1 ;
                1 1 1 0 0 0 1 1 1 1 0 0 0 1 1 1 ;
                1 1 1 0 0 0 1 1 1 1 0 0 0 1 1 1 ;
                1 1 1 0 0 0 1 1 1 1 0 0 0 1 1 1 ;
                1 1 1 0 0 0 1 1 1 1 0 0 0 1 1 1 ;
                1 1 1 0 0 0 1 1 1 1 0 0 0 1 1 1 ;
                1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 ;
                1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 ;
                ];
        else
            ico = [
                1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 ;
                1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 ;
                1 1 1 0 0 1 1 1 1 1 1 1 1 1 1 1 ;
                1 1 1 0 0 0 0 1 1 1 1 1 1 1 1 1 ;
                1 1 1 0 0 0 0 0 0 1 1 1 1 1 1 1 ;
                1 1 1 0 0 0 0 0 0 0 0 1 1 1 1 1 ;
                1 1 1 0 0 0 0 0 0 0 0 0 0 1 1 1 ;
                1 1 1 0 0 0 0 0 0 0 0 0 0 0 0 1 ;
                1 1 1 0 0 0 0 0 0 0 0 0 0 0 0 1 ;
                1 1 1 0 0 0 0 0 0 0 0 0 0 1 1 1 ;
                1 1 1 0 0 0 0 0 0 0 0 1 1 1 1 1 ;
                1 1 1 0 0 0 0 0 0 1 1 1 1 1 1 1 ;
                1 1 1 0 0 0 0 1 1 1 1 1 1 1 1 1 ;
                1 1 1 0 0 1 1 1 1 1 1 1 1 1 1 1 ;
                1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 ;
                1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 ;
                ];

        end
        if ndims(ico)==2
            ico = ico*0.95;
            ico = repmat(ico,[1 1 3]);
        end
    otherwise
        filename = fullfile(fileparts(mfilename("fullpath")),'Icons',[button.Tag,'.png']);
        if exist(filename,'file')
            ico = imread(filename);
        else
            logmsg(['Icon for action ' button.Tag ' not yet defined.'])
            ico = [
                1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 ;
                1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 ;
                1 1 0 0 1 1 1 1 1 1 1 1 1 0 0 1 ;
                1 1 1 0 0 1 1 1 1 1 1 1 0 0 1 1 ;
                1 1 1 1 0 0 1 1 1 1 1 0 0 1 1 1 ;
                1 1 1 1 1 0 0 1 1 1 0 0 1 1 1 1 ;
                1 1 1 1 1 1 0 0 1 0 0 1 1 1 1 1 ;
                1 1 1 1 1 1 1 0 0 0 1 1 1 1 1 1 ;
                1 1 1 1 1 1 1 0 0 0 1 1 1 1 1 1 ;
                1 1 1 1 1 1 0 0 1 0 0 1 1 1 1 1 ;
                1 1 1 1 1 0 0 1 1 1 0 0 1 1 1 1 ;
                1 1 1 1 0 0 1 1 1 1 1 0 0 1 1 1 ;
                1 1 1 0 0 1 1 1 1 1 1 1 0 0 1 1 ;
                1 1 0 0 1 1 1 1 1 1 1 1 1 0 0 1 ;
                1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 ;
                1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 ;

                ];
            ico = ico*0.95;
            ico = repmat(ico,[1 1 3]);
        end
end
button.CData = ico;
end


