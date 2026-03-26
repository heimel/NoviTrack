function [overhead_x, overhead_y] = nt_change_camera_to_overhead_coordinates(camera_x, camera_y, params)
%nt_change_camera_to_overhead. Changes real world camera centered coordinates to overhead image coordinates
%
%  [overhead_x, overhead_y] = nt_change_camera_to_overhead_coordinates(camera_x, camera_y, params)
%
% 2024-2025, Alexander Heimel

distort = params.overhead_camera_distortion;

switch params.overhead_camera_distortion_method
    case 'normal'
        scale = distort(1);

        [theta, camera_r] = cart2pol(camera_x,camera_y);
        overhead_r = camera_r * scale;
        [overhead_x, overhead_y] = pol2cart(theta,overhead_r);
    case 'fisheye_log' % deprecated
        distort = distort(1);

        [theta, camera_r] = cart2pol(camera_x,camera_y);
        overhead_r = log(camera_r*distort+1)/distort;
        [overhead_x, overhead_y] = pol2cart(theta,overhead_r);

        overhead_x = overhead_x / params.overhead_camera_shear(1);
        overhead_y = overhead_y / params.overhead_camera_shear(2);
    case 'fisheye_equidistant' % deprecated
        % following formula from https://www.imatest.com/docs/pre-distorted-charts
        % check for corrections at https://euratom-software.github.io/calcam/html/intro_theory.html
        % https://en.wikipedia.org/wiki/Fisheye_lens#Mapping_function
        %
        % overhead_r = f * camera_phi, with phi angle from camera
        % normal and f focal distance

        distance_neurotar_center_to_camera_mm = distort(1); % e.g. 270
        focal_distance_pxl = distort(2); % e.g 260

        [theta, camera_r] = cart2pol(camera_x, camera_y);
        camera_phi = atan( camera_r / distance_neurotar_center_to_camera_mm );   
        overhead_r = focal_distance_pxl * camera_phi;
        [overhead_x, overhead_y] = pol2cart(theta,overhead_r);
    case 'fisheye_orthographic'
        % following formula from https://www.imatest.com/docs/pre-distorted-charts
        % check for corrections at https://euratom-software.github.io/calcam/html/intro_theory.html
        % https://en.wikipedia.org/wiki/Fisheye_lens#Mapping_function
        %
        % overhead_r = f * sin(camera_phi), with phi angle from camera
        % normal and f focal distance

        distance_neurotar_center_to_camera_mm = distort(1); % e.g. 270
        focal_distance_pxl = distort(2); % e.g 260

        [theta, camera_r] = cart2pol(camera_x, camera_y);
        overhead_r  = focal_distance_pxl * sin(atan( camera_r / distance_neurotar_center_to_camera_mm ));   
        [overhead_x, overhead_y] = pol2cart(theta,overhead_r);

end

overhead_x = overhead_x + params.overhead_camera_width/2 - params.overhead_camera_image_offset(1);
overhead_y = overhead_y + params.overhead_camera_height/2 - params.overhead_camera_image_offset(2);
end