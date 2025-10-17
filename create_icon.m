function ico = create_icon(ch,varargin)

p = inputParser;
addRequired(p,'ch',@(s)ischar(s) || (isstring(s) && strlength(s)==1));
addParameter(p,'FontName','Arial',@(s)ischar(s)||isstring(s));
addParameter(p,'FontSize',180,@(x)isnumeric(x)&&isscalar(x)&&x>0);
addParameter(p,'Bold',false,@islogical);
addParameter(p,'Italic',false,@islogical);
addParameter(p,'Color',[0 0 0]);
addParameter(p,'BackgroundColor',[0.95 0.95 0.95]);

parse(p,ch,varargin{:});
opt = p.Results;
ch = char(opt.ch);
CANVAS = 256;

I = zeros(CANVAS, CANVAS, 'uint8');           % black background
style = {};
if opt.Bold,   style = [style, {'FontWeight','bold'}];   end %#ok<AGROW>
if opt.Italic, style = [style, {'FontAngle','italic'}];  end %#ok<AGROW>

% Centered text; no box; white text for simple thresholding.
RGB = insertText(I, [CANVAS/2, CANVAS/2], ch, ...
    'Font', opt.FontName, ...
    'FontSize', opt.FontSize, ...
    'AnchorPoint','Center', ...
    'BoxOpacity', 0, ...
    'TextColor', 'white', ...
    style{:});

G = rgb2gray(RGB);                  % uint8
BW = G > 0;                         % white text on black background


% --------- trim whitespace, pad to square, resize ---------
% Tight bounding box
rows = find(any(BW,2));
cols = find(any(BW,1));
if isempty(rows) || isempty(cols)
    icon16 = false(16,16);  % empty glyph fallback
    return;
end
BWc = BW(rows(1):rows(end), cols(1):cols(end));

% Pad to square
[h, w] = size(BWc);
if h > w
    pad = h - w;
    left  = floor(pad/2);
    right = pad - left;
    BWsq = padarray(BWc, [0 left], 0, 'pre');
    BWsq = padarray(BWsq, [0 right], 0, 'post');
elseif w > h
    pad = w - h;
    top    = floor(pad/2);
    bottom = pad - top;
    BWsq = padarray(BWc, [top 0], 0, 'pre');
    BWsq = padarray(BWsq, [bottom 0], 0, 'post');
else
    BWsq = BWc;
end

% Resize to 16x16. Use 'box' antialiasing (via default) then threshold.
I16 = imresize(single(BWsq), [16 16], 'bilinear');   % smooth downsample
chico = I16 > 0.5;                                  % final logical


bg_color = opt.BackgroundColor;
ico = ones([16 16])-chico;
ico = repmat(ico,1,1,3);
ico = bsxfun(@times, ico, reshape(bg_color, 1, 1, 3));
ico = ico + bsxfun(@times, chico, reshape(opt.Color, 1, 1, 3));
end