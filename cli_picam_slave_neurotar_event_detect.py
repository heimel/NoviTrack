# picam_slave_neurotar.py
#  
#    reads acqReady to start video recording
#    while listening to GPIO pin 17
#
# 2023, Alexander Heimel

from picamera import PiCamera
from datetime import datetime
import serial
import time
import sys
import csv
import os
import RPi.GPIO as GPIO
import socket # for gethostname
import json
#from pynput import keyboard
import acquisition_slave


#def on_press(key):
#    pass
#    try:
#        print('alphanumeric key {0} pressed'.format(
#            key.char))
#    except AttributeError:
#        print('special key {0} pressed'.format(
#            key))

#def on_release(key):
#    print('{0} released'.format(key) + '. Press Escape to exit.')
#    if key == keyboard.Key.esc:
#        # Stop listener
#        return False

session_path = acquisition_slave.read_acqready( 'Neurotar' )
print('PICAM_SLAVE_NEUROTAR:' + session_path)
if not os.path.isdir(session_path):
    error_message = "Error: Not existing " + session_path
    print(error_message)
    sys.exit(error_message)

session_json = acquisition_slave.read_session_json( session_path )
session_name = os.path.basename(session_path)

hostname = socket.gethostname()

video_filename = os.path.join(session_path , session_name + "_" + hostname + '.h264')
print("Checking existence of " + video_filename)
if os.path.exists(video_filename):
    sys.exit(video_filename + " already exists. Exiting.")

triggers_filename = os.path.join(session_path, session_name +  "_" + hostname + '_triggers.csv')
print("Checking existence of  " + triggers_filename)
if os.path.exists(triggers_filename):
    sys.exit(triggers_filename + " already exists. Exiting.");

#initialize camera
camera = PiCamera()
camera.resolution = (752, 582)
camera.framerate = 30
#camera.awb_mode = 'greyworld'
camera.awb_mode = 'off'
rg, bg = (1.0, 1.5)
camera.awb_gains = (rg, bg)
camera.exposure_mode = 'night'

#initialize serial
#ser = serial.Serial(port = '/dev/ttyS0', baudrate = 115200)

# Initialize GPIO pin
butPin = 17 # Broadcom pin 17 (P1 pin 11)
GPIO.setmode(GPIO.BCM) # Broadcom pin-numbering scheme
GPIO.setup(butPin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # Button pin set as input w/ pull-up
boolPinState = False

#pre-allocate
triggercount = 0
triggerframes = []

#start recording
#listener = keyboard.Listener(
#    on_press=on_press,
#    on_release=on_release)
#listener.start()

start_time = 0

def ttl_callback(channel):
    frame_ind = camera.frame.index
    current_time = datetime.now()
    elapsed_time = current_time - start_time

    triggerframes.append([frame_ind,current_time.strftime("%H:%M:%S.%f"),elapsed_time.total_seconds()])

    print("Received trigger at " + current_time.strftime("%H:%M:%S.%f") + ". Elapsed time = " + str(elapsed_time.total_seconds()) )
    print(frame_ind)



GPIO.add_event_detect(butPin, GPIO.RISING, callback=ttl_callback)

time.sleep(0.1)

camera.start_preview(fullscreen=False, window = (200, 50, 640, 480))

camera.start_recording(video_filename)




start_time = datetime.now()
frame_ind = camera.frame.index

current_time = datetime.now()
elapsed_time = current_time - start_time
print("Started recording at " + start_time.strftime("%H:%M:%S.%f") + ". Press Escape to stop.")
print(frame_ind)

triggerframes.append([frame_ind,start_time.strftime("%H:%M:%S.%f"),elapsed_time.total_seconds()])



                
main_loop = True
try:
    while main_loop:
        time.sleep(1) # check every second if not stopped
finally:
    print("Stopping recording.")
    #listener.stop()
    
    camera.stop_preview()
    camera.stop_recording()
    
    #write triggerframes to file
    print("Writing to " + triggers_filename )
    f = open(triggers_filename, 'w')
    csvWriter = csv.writer(f)
    csvWriter.writerow(['frame','time'])
    i = 0
    while i < len(triggerframes):
        csvWriter.writerow(triggerframes[i])
        i += 1
    f.close()

    GPIO.cleanup()
    
    print('Done.')
    print("To convert to mp4: MP4Box -add filename.h264:fps=30 -fps original -new filename.mp4" )
    print('To install on linux: sudo apt-get install gpace')
        
    
