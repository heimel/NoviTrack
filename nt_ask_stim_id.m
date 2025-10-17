function stim_id = nt_ask_stim_id(handles,max_id)
%nt_ask_stim_id. Ask for stim_id 1,2,...
%
% stim_id = nt_ask_stim_id(HANDLES,MAX_ID = 9)
%
% 2025, Alexander Heimel


if nargin<1 || isempty(handles)
    handles = [];
end
if nargin<2 || isempty(max_id)
    max_id = 9;
end

if ~isempty(handles)
    set(handles.text_state,'String','Choose stim');
end

% stim_id = dialog_with_grid(max_id);
% return

% stim_id = NaN;
% while isnan(stim_id)
%     fprintf('Choose which stim_id (1,2,...) by pressing number key: ')
%     drawnow
%     waitforbuttonpress;
%     key = get(gcf,'CurrentCharacter');
%     fprintf([key '\n']);
%     stim_id = str2double(key);
%     if isnan(stim_id)
%         disp([key ' is not a digit. Choose again.']);
%     end
% end
% end
% 
% function stim_id = dialog_with_grid(max_id)

% open dialog around mouse location
mp = get(0, 'PointerLocation');  % [x, y] in pixels from bottom-left corner
w = 50 * max_id;
h = 50;

x = mp(1) - w/2;
y = mp(2) - h/2;

fig = uifigure('Name', 'Choose stimulus id', ...
    'Position', [x y w h],'WindowStyle', 'modal');

gl = uigridlayout(fig, [1,max_id]);

labels = {'1','2','3','4','5','6','7','8','9'};
for i = 1:max_id
    uibutton(gl, 'Text', labels{i}, ...
        'ButtonPushedFcn',  @(btn, event) on_choice(btn.Text));
end
fig.KeyPressFcn = @(key,event) on_choice(event.Key);
uiwait(fig);

    function on_choice(choice)
        stim_id = str2double(choice);
        if ~isnan(stim_id) && stim_id<=max_id && stim_id>0
            uiresume(fig);  % continue execution
            delete(fig);    % close dialog
        end
    end

    
end

