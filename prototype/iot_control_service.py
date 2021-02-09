# face recognition module
import face_recognition
import cv2
import numpy as np
# pychromecast -> smart speaker module
import os
import time
import http.server
import socket
import threading
import pychromecast
from gtts import gTTS
# hue controller module
from configparser import ConfigParser
from hue_local_controller import HueLocalController
# activity recognition
from activity_recognition import action_recog
# pychromecast youtube player
from pychromecast.controllers.youtube import YouTubeController
# openwrt -> access page management
from openwrt_check import openwrt_main
import pickle
# speech recognition
from speech_recognition import stt_test1

# load model
get_recog_model = action_recog()
model = get_recog_model.get_model() # using this model!!

# setting smart speaker
# get my local ip address
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
    s.connect(('8.8.8.8', 80))
    local_ip, _ = s.getsockname()

# set up a simple server
PORT = 8000

class StoppableHTTPServer(http.server.HTTPServer):
    def run(self):
        try:
            print('Server started at %s:%s!' % (local_ip, self.server_address[1]))
            self.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            self.server_close()

# start server in background
server = StoppableHTTPServer(('', PORT), http.server.SimpleHTTPRequestHandler)
thread = threading.Thread(None, server.run)
thread.start()

# connect to Google Nest Hub
chromecasts, browser = pychromecast.get_listed_chromecasts(friendly_names=["Office"])
ghome = chromecasts[0]
ghome.wait()

os.makedirs('cache', exist_ok=True)
fname = 'cache/cache.mp3'

mc = ghome.media_controller
def speechtospeaker(say, langu):
    global local_ip
    global PORT
    global fname
    global mc
    
    tts = gTTS(say, lang=langu)
    tts.save(fname)

    mp3_path = 'http://%s:%s/%s' % (local_ip, PORT, fname)
    mc.play_media(mp3_path, 'audio/mp3')

    # pause atm
    mc.block_until_active()
    mc.pause()

    mc.play()
    while not mc.status.player_is_idle: 
        time.sleep(1)
    mc.stop()
# ======================================================
# hue controller setting
parser = ConfigParser()
parser.read('hue_info.ini')

hueLocalController = HueLocalController(parser.get('LOCALBRIDGE','bridge_ip'),
						parser.get('LOCALBRIDGE','username'))

hue_lights = hueLocalController.lights_scan()
# face detection -> predict user name
face_locations = list()
face_encodings = list()

def detection_predict_user(rgb_frame):
    global known_face_encodings
    global known_face_names

    face_locations = face_recognition.face_locations(rgb_frame)
    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

    face_names = list()
    for face_encoding in face_encodings:
        matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
        name = "Unknown"

        face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
        best_match_index = np.argmin(face_distances)
        if matches[best_match_index]:
            name = known_face_names[best_match_index]

        face_names.append(name)
        # if unknown face -> save image to unknown file
        if name == "Unknown":
            print("There are unknown faces on the screen. Save the image file. Path : ./face_img/unknown/")
            cv2.imwrite('./face_img/unknown/unknown_' + str(time.time()) + '.jpg', frame)

    if len(face_names) != 0:
        return face_names[0]
    else:
        return ''

# ======================================================
# action detection wash -> youtube controller (play youtube)
def play_youtube(video_id):
    global ghome

    yt = YouTubeController()
    ghome.register_handler(yt)
    yt.play_video(video_id)

    while yt.is_active:
        time.sleep(1)

# ======================================================
# openwrt load file information setting
ow_class = openwrt_main.openwrt_class("root", "192.168.1.1")

def save_packet_capture_file():
    global ow_class

    ow_class.capture_packet()
    res = ow_class.check_blacklist()
    if res == '2':
        say = 'This is not normal site access. We recommend that you do not log in.'
        speechtospeaker(say, 'en')

# ======================================================
# speech recognition class
sr_class = stt_test1.Speech_to_Text('test')
positive_list = ['응', '좋아', '알았어']

# ======================================================


video_capture = cv2.VideoCapture(1)

# unknown face image
path = './face_img/unknown/'
unface_list = os.listdir(path)
if len(unface_list) != 0:
    say = ''' There is an unrecognizable person among the face files. please check. '''
    speechtospeaker(say, 'en')

path = "./face_img/known/"
face_list = os.listdir(path)

known_face_encodings = list()
known_face_names = list()
for fl in face_list:
    face_image = face_recognition.load_image_file(path + fl)
    known_face_encodings.append(face_recognition.face_encodings(face_image)[0])
    known_face_names.append(fl.split(',')[0])

# check in people
check_inner_people = list()
# check laptop usage people
usage_laptop_user = dict()
while True:
    ret, frame = video_capture.read()
    small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
    rgb_small_frame = small_frame[:, :, ::-1]

    # Display the results
    for (top, right, bottom, left), name in zip(face_locations, face_names):
        # Scale back up face locations since the frame we detected in was scaled to 1/4 size
        top *= 4
        right *= 4
        bottom *= 4
        left *= 4

        # Draw a box around the face
        cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)

        # Draw a label with a name below the face
        cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
        font = cv2.FONT_HERSHEY_DUPLEX
        cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)

    # Display the resulting image
    cv2.imshow('Video', frame)

    # for predict human action
    img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    img = cv2.resize(img, (224, 224), cv2.INTER_AREA)
    prediction = model.predict(np.array([img]))
    class_names = ['book', 'laptop', 'phone', 'wash', 'water']
    argmax_predict = np.argmax(prediction[0])
    predict_value = prediction[argmax_predict]
    predict_class = class_names[argmax_predict]
    
    if predict_value > 0.85:
        # action book -> hue turn on
        if predict_class == 'book':
            for hl in hue_lights.keys():
                hueLocalController.detect_me(lightnumber=hl)
        
        # action water -> fitbit connection
        elif predict_class == 'water':
            manage_drink = True

            user_name = detection_predict_user(rgb_small_frame)
            if user_name == '':
                say = 'Someone I don\'t know is drinking water. Can I manage it?'
                speechtospeaker(say, 'en')

                res_people = sr_class.main()[:-5]
                if res_people not in res_predict_list:
                    manage_drink = False
                else:
                    say = 'What\'s your name?'
                    speechtospeaker(say, 'en')
                    user_name = sr_class.main()[:-5]

            if manage_drink:
                drink_status = dict()
                with open('./water_manage/people_water.pickle', 'rb') as fr:
                    drink_status = pickle.load(fr)

                if user_name not in list(drink_status.keys()):
                    drink_status[user_name] = 1 # Save as 1 cup
                else:
                    drink_status[user_name] += 1 # 1 cup increase from previous
        
        # action laptop -> manage usage time
        elif predict_class == 'laptop':
            # Checking the router's MAC address
            name_mac = ow_class.get_rental_equipment_file()
            if len(name_mac) == 0:
                say = 'Currently, the Wi-Fi that the computer is connected to is not subject to management. I can\'t take care of it, but don\'t use it for too long.'
                speechtospeaker(say, 'en')

            # manage usage time
            for name in name_mac:
                if name not in usage_laptop_user: # name is mac address
                    usage_laptop_user[name] = [time.time(), 0, name_mac[name]] # [start time, usage time, device name]
                else:
                    temp_usage_laptop = usage_laptop_user[name]
                    temp_usage_laptop[1] = time.time() - temp_usage_laptop[0]
                    usage_laptop_user[name] = temp_usage_laptop

        # action wash -> youtube play
        elif predict_class == 'wash':
            say = 'Today, I will play an exciting song to help you a little while washing the dishes.'
            speechtospeaker(say, 'en')
            
            VIDEO_ID = 'LHfN1DiRB18' # video id is the last part of the url http://youtube.com/watch?v=video_id
            play_youtube(VIDEO_ID)
        
        # action phone -> manage usage time and block harmful sites
        elif predict_class == 'phone':
            manage_usage_phone = True

            user_name = detection_predict_user(rgb_small_frame)
            if user_name == '':
                say = 'This is someone I don't know. If you are a cleaning lady when using a mobile phone, would you manage it?'
                speechtospeaker(say, 'en')

                res_people = sr_class.main()[:-5]
                if res_people not in positive_list:
                    manage_usage_phone = False

            if manage_usage_phone:
                thread_packet_capture = threading.Thread(None, save_packet_capture_file)
                thread_packet_capture.start()

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

video_capture.release()
cv2.destroyAllWindows()

# kill all
ghome.quit_app()
server.shutdown()
thread.join()
thread_name.join()