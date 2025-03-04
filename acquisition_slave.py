# acquisition_slave
#
#  2023, Alexander Heimel

import os
import json

def read_acqready( setup):
    # returns sessions path specifiec in acqReady
    root_communication_path = os.path.join(os.path.sep+os.path.sep,"VS03.herseninstituut.knaw.nl",'VS03-CSF-1','Communication')
    communication_path = os.path.join(root_communication_path, setup)
    acqready_filename = os.path.join(communication_path,'acqReady')
    print('ACQUISITION_SLAVE: Reading ' + acqready_filename)
    acqready_file = open(acqready_filename, 'r')
    acqready_file.readline() # remove pathSpec header
    session_path = acqready_file.readline().strip()
    acqready_file.close()
    session_path = os.path.sep + os.path.join(*session_path.split('\\'))
    print("ACQUISITION_SLAVE: Session path = " + session_path)
    return session_path

def read_session_json(session_path):
    # returns session json in session path
    session_name = os.path.basename(session_path)
    json_filename = os.path.join( session_path, session_name + '_session.json' )
    print(json_filename)
    json_file = open(json_filename, 'r')
    session_json = json.load(json_file)
    json_file.close()
    print(session_json)
    return session_json

#setup = 'Neurotar'
#session_path = read_acqready( setup )
#session_json = read_session_json( session_path )
