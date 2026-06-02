# nt_picam_slave.py
#  
#    reads acqReady to start video recording
#    while listening to GPIO pin 17
#    saving log to session_path from acqReady
#
#    First command line argument is taken as setup for 
#    determining the communication folder.
#
# 2023-2025, Alexander Heimel

from picamera2 import Picamera2, Preview
from picamera2.encoders import H264Encoder
from picamera2.outputs import FileOutput
from datetime import datetime
import time
import sys
import csv
import os
import RPi.GPIO as GPIO
import socket # for gethostname
import json
#from pynput import keyboard
import acquisition_slave
import signal

stop_requested = False

def signal_handler(sig, frame):
    global stop_requested
    print("Stop requested...")
    stop_requested = True

signal.signal(signal.SIGINT, signal_handler)


setup = sys.argv[1] if len(sys.argv) > 1 else 'Neurotar'

session_path = acquisition_slave.read_acqready(setup)
print('CLI_PICAM_SLAVE:' + session_path)
if not os.path.isdir(session_path):
    error_message = "Error: Not existing " + session_path
    print(error_message)
    sys.exit(error_message)

session_json = acquisition_slave.read_session_json(session_path)

ttl_setup = session_json['setup']

if ttl_setup == 'Neurotar': 
    sources = {
        27: 'sync_ttl',
        17: 'neurotar'        
        }
    
else:
    sources = {
        17: 'sync_ttl'        
        }
    
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
camera = Picamera2()
rg, bg = (1.0, 1.5) # for neurotar room


video_config = camera.create_video_configuration(
    main={"size": (752, 582), "format": "YUV420"},
    controls={"FrameRate": 30}
)
camera.configure(video_config)

# AWB / exposure (limited support in Picamera2)
camera.set_controls({
    "AwbEnable": True,
    "ExposureTime": 0,  # auto
    "ColourGains": (rg, bg)
})

# encoder setup (may need to change these later)
encoder = H264Encoder(bitrate=10000000)
output = FileOutput(video_filename)

# Initialize GPIO pin
GPIO.setmode(GPIO.BCM)
pin_states = {}
for pin in sources:
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP) # connfigures which pins are to be used as inputs
    pin_states[pin] = GPIO.input(pin) # state of pin (0/LOW/False or 1/HIGH/True)
    
# GPIO.setmode(GPIO.BCM) # Broadcom pin-numbering scheme
# GPIO.setup(butPin, GPIO.IN, pull_up_down=GPIO.PUD_UP) # Button pin set as input w/ pull-up
# boolPinState = GPIO.input(butPin)

#pre-allocate
triggercount = 0
triggerframes = []
start_time = 0
frame_ind = 0 #     frame_ind = camera.frame.index


def ttl_callback(channel):
    
    if stop_requested:
        return
    
    global pin_states
    global frame_ind #     frame_ind = camera.frame.index

    current_time = datetime.now()
    elapsed_time = current_time - start_time
    frame_ind = int(elapsed_time.total_seconds() * 30)
    
    # Only log rising edge (LOW to HIGH)
    if GPIO.input(channel) == True and pin_states[channel] == False:
        triggerframes.append([
            frame_ind,
            current_time.strftime("%H:%M:%S.%f"),
            elapsed_time.total_seconds(),
            sources[channel],
            'recieved'
        ])
        # print(f"Trigger on {sources[channel]} at {current_time.strftime('%H:%M:%S.%f')}. Elapsed: {elapsed_time.total_seconds()} s")
        print("Recieved " + sources[channel] + " trigger at " + current_time.strftime('%H:%M:%S.%f') + ". Elapsed: " + str(elapsed_time.total_seconds()) )

    else:
        print("Ignored change on " + sources[channel] + " at " + current_time.strftime('%H:%M:%S.%f'))
        
        # dirty fix for now, in case a real pulse was not 'received'. caveat is that i'm not sure where in the ttl pulse the ignored change is detected
        triggerframes.append([
            frame_ind,
            current_time.strftime("%H:%M:%S.%f"),
            elapsed_time.total_seconds(),
            sources[channel],
            'ignored'
        ])
    
    pin_states[channel] = GPIO.input(channel)
        
for pin in sources:
    GPIO.add_event_detect(pin, GPIO.BOTH, callback=ttl_callback, bouncetime = 10)
    
time.sleep(0.1)

#camera.start_preview(fullscreen=False, window = (200, 50, 640, 480))
try:
    camera.start_preview(Preview.QTGL) # need to enable Glamor on Pi 3 or older
except:
    camera.start()

#camera.start_recording(video_filename)
camera.start_recording(encoder, output)

start_time = datetime.now()
frame_ind = 0
current_time = datetime.now()
elapsed_time = current_time - start_time
print("Started recording at " + start_time.strftime("%H:%M:%S.%f") + ". Press Escape to stop.")
print(frame_ind)
triggerframes.append([
    frame_ind,
    start_time.strftime("%H:%M:%S.%f"),
    0.0,
    'start',
    'none'
])                              
main_loop = True
try:
    print('Started loop. Waiting for Ctrl-c to exit')
    while not stop_requested:
        time.sleep(1) # check every second if not stopped
        #  camera.wait_recording(1) # (wait_recording not in picamera2)

finally:
    
    for pin in sources: # prevents callback from firing when encoder shuts down
        GPIO.remove_event_detect(pin)
        
    print("Stopping recording.")
    time.sleep(0.5)
    camera.stop_recording()
    camera.stop()
    
    #write triggerframes to file
    print("Writing to " + triggers_filename )
    f = open(triggers_filename, 'w')
    csvWriter = csv.writer(f)
    csvWriter.writerow(['frame','time', 'time elapsed (s)', 'ttl source', 'input type'])
    i = 0
    while i < len(triggerframes):
        csvWriter.writerow(triggerframes[i])
        i += 1
    f.close()

    GPIO.cleanup()
    
    print('Done.')
    print("To convert to mp4: MP4Box -add filename.h264:fps=30 -fps original -new filename.mp4" )
    print('To install on linux: sudo apt-get install gpace')
        
print('NT_PICAM_SLAVE: end of recording' )
