print('DEPRECATED. USE picam_slave_neutor.py INSTEAD')


projectID = '22.35.01' #str, Study Dossier 22.35.01
mouseID = 'test' #str
session = 12
#int

# For converting h264 to mp4
# sudo apt-get install gpac


##################################
#import necessary packages
from picamera import PiCamera
from datetime import datetime
import serial
import time
import sys
import csv
import os
import RPi.GPIO as GPIO
import socket # for gethostname
#import keyboard # for exiting while 


from pynput import keyboard


def on_press(key):
    try:
        print('alphanumeric key {0} pressed'.format(
            key.char))
    except AttributeError:
        print('special key {0} pressed'.format(
            key))

def on_release(key):
    print('{0} released'.format(key))
    if key == keyboard.Key.esc:
        # Stop listener
        return False

listener = keyboard.Listener(
    on_press=on_press,
    on_release=on_release)
listener.start()

genOutputPath = '/mnt/VS03-CSF-1/Ren/Innate_approach/Data_collection'
today = datetime.today().strftime('%Y%m%d')


experimentName = mouseID + '_' + today + '_' '{0:03}'.format(session)

outputDir = os.path.join(genOutputPath, projectID, mouseID, experimentName)
if not os.path.isdir(outputDir):
    os.makedirs(outputDir)
    print("Created " + outputDir )

#create output file name
hostname = socket.gethostname()

vidFullFileName = outputDir + '/' + experimentName + "_" + hostname + '.h264'
print("Checking existence of " + vidFullFileName)
if os.path.exists(vidFullFileName):
    print(vidFullFileName + " already exists. Quitting.");
    sys.exit('You tried overwriting existing files!')
csvFullFileName = outputDir + '/' + experimentName +  "_" + hostname + '_triggers.csv'
print("Checking existence of  " + csvFullFileName)
if os.path.exists(csvFullFileName):
    print(csvFullFileName + " already exists. Quitting.");
    sys.exit('You tried overwriting existing files!')

#initialize camera
camera = PiCamera()
camera.resolution = (752, 582)
camera.framerate = 30

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
camera.start_preview(fullscreen=False, window = (200, 50, 640, 480))
camera.start_recording(vidFullFileName)


print("Started recording. Press Escape to stop.")

main_loop = True

try:
    while listener.running:
        if GPIO.input(butPin):
            if not boolPinState:
                triggerframes.append(camera.frame.index)
                triggercount += 1
                now = datetime.now()
                current_time = now.strftime("%H:%M:%S")
                print("Received trigger " + str(triggercount) + " at " + current_time ) 
            boolPinState = True
        else:
            boolPinState = False
#        if keyboard.is_pressed('q'):
#           print("Pressed q.")
#            break        
finally:
    print("Stopping recording.")
    listener.stop()
    
    # stop camera
    camera.stop_preview()
    camera.stop_recording()
    
    #write triggerframes to file
    print("Writing to " + csvFullFileName )
    f = open(csvFullFileName, 'w', newline = '')
    csvWriter = csv.writer(f)
    csvWriter.writerow(['frame'])
    i = 0
    while i < len(triggerframes):
        csvWriter.writerow([triggerframes[i]])
        i += 1
    f.close()
    
    print('Done!')
    print("Use MP4Box -add filename.h264 filename.mp4" )
        
    
