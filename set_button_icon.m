function set_button_icon(button,arg)
%set_button_icon. Sets icon on button
%
%  set_button_icon(BUTTON,ARG)
% 
%      BUTTON is handle to button object
%      ARG is dependent on button type
%
% 2025, Alexander Heimel

switch button.Tag
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
        ico = ico*0.95;
        ico = repmat(ico,[1 1 3]);
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