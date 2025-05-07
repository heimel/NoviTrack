function [camera_x, camera_y] = nt_change_overhead_to_camera_coordinates(overhead_x,overhead_y,params)
%nt_change_camera_to_overhead_coordinates. Changes real world camera centered coordinates to overhead image coordinates
%
%  [camera_x, camera_y] = nt_change_overhead_to_camera_coordinates(overhead_x,overhead_y,params)
%
% 2024, Alexander Heimel

distort = params.overhead_camera_distortion;

overhead_x = overhead_x - params.overhead_camera_width/2 + params.overhead_camera_image_offset(1);
overhead_y = overhead_y - params.overhead_camera_height/2 + params.overhead_camera_image_offset(2);



switch params.overhead_camera_distortion_method
    case 'normal'
        scale = distort(1);

        [theta,overhead_r] = cart2pol(overhead_x,overhead_y);
        camera_r = overhead_r/scale;
        [camera_x,camera_y] = pol2cart(theta,camera_r);
    case 'fisheye_log'
        distort = distort(1);

        overhead_x = overhead_x * params.overhead_camera_shear(1);
        overhead_y = overhead_y * params.overhead_camera_shear(2);

        [theta,overhead_r] = cart2pol(overhead_x,overhead_y);
        camera_r = (exp(overhead_r*distort)-1)/distort;
        [camera_x,camera_y] = pol2cart(theta,camera_r);

    case 'fisheye_equidistant'
        % following formula from https://www.imatest.com/docs/pre-distorted-charts
        % check for corrections at https://euratom-software.github.io/calcam/html/intro_theory.html
        % https://en.wikipedia.org/wiki/Fisheye_lens#Mapping_function
        %
        % overhead_r = f * camera_phi, with phi angle from camera
        % normal and f focal distance
        %
        % distort(1) = distance_neurotar_center_to_camera_mm
        % distort(2) = focal_distance_pxl
        %
        % inversion is incorrect for large angles!

        distance_neurotar_center_to_camera_mm = distort(1);
        focal_distance_pxl = distort(2);

        [theta,overhead_r] = cart2pol(overhead_x, overhead_y);
        overhead_phi = overhead_r / focal_distance_pxl;
        camera_r = distance_neurotar_center_to_camera_mm * tan(overhead_phi);
        [camera_x, camera_y] = pol2cart(theta, camera_r);


    case 'fisheye_orthographic'
        % following formula from https://www.imatest.com/docs/pre-distorted-charts
        % check for corrections at https://euratom-software.github.io/calcam/html/intro_theory.html
        % https://en.wikipedia.org/wiki/Fisheye_lens#Mapping_function
        %
        % overhead_r = f * sin(camera_phi), with phi angle from camera
        % normal and f focal distance
        %
        % distort(1) = distance_neurotar_center_to_camera_mm
        % distort(2) = focal_distance_pxl
        %
        % inversion is incorrect for large angles!

        distance_neurotar_center_to_camera_mm = distort(1);
        focal_distance_pxl = distort(2);

        [theta,overhead_r] = cart2pol(overhead_x, overhead_y);

        if overhead_r>focal_distance_pxl
            logmsg('Point outside camera view')
            overhead_r = focal_distance_pxl;
            camera_x = NaN;
            camera_y = NaN;
            return

        end
        
        camera_r = distance_neurotar_center_to_camera_mm * tan(asin(overhead_r / focal_distance_pxl));
        [camera_x, camera_y] = pol2cart(theta, camera_r);

end



end