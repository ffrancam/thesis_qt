#!/usr/bin/env python3
import sys
import threading
import rospy
import numpy as np
from std_msgs.msg import String
from qt_robot_interface.srv import *
from qt_gesture_controller.srv import *
from qt_nuitrack_app.msg import Faces
from synchronizer import TaskSynchronizer
import azure.cognitiveservices.speech as speechsdk

from thesis_qt.srv import EmotionConverter

try:
    from qt_vosk_app.srv import *
except:
    pass

try:
    from qt_riva_asr_app.srv import *
except:
    pass

class QTRobot:

  REPEAT_TRIGGERS = [
    "non ho capito", "ripeti", "cosa hai detto", "non capisco",
    "puoi ripetere", "ripetere", "non ho sentito", "cosa", "eh",
    "ripeterà", "potresti ripeterà", "puoi ripeterà", "ripetere?",
    "potresti ripetere", "puoi ripete",
  ]

  YES_TRIGGERS = [
    "sì", "si", "certo", "esatto", "ovviamente", "assolutamente",
    "senz'altro", "già", "esattamente", "confermo", "ok", "okay",
    "va bene", "d'accordo", "giusto", "perfetto", "certamente"
  ]

  NO_TRIGGERS = [
      "no", "nope", "negativo", "per niente", "assolutamente no",
      "neanche", "nemmeno", "non credo", "non direi", "macché",
      "niente affatto", "no grazie"
  ]

  def __init__(self):

    self.ts = TaskSynchronizer()

    self.tts_voice = rospy.get_param("/offline_conversation/tts_voice", 'it_IT')
    self.asr_language = rospy.get_param("/offline_conversation/asr_language", 'it_IT')

    self.is_face_visible = False
    self.current_user_emotion = "N"

    self.emotion_map = {
      "H": np.array([3.44, 2.93, 0.92]),
      "F":np.array([-2.37, -1.04, -0.71]),
      "A":np.array([-1.77, 0.57, 1.8]),
      "SA":np.array([-2.29, -1.44 , -2.04]),
      "SU": np.array([0.5, 2.5, 3.19]),
      "D": np.array([-2.27, 0.22, 0.43]),
      "N": np.array([0.58, 0.75, 0.56]),
      "B": np.array([-1.85, -0.86, -2.01])
    }

    self.emotion_map_squared = {
      "H": np.array([11.8336, 8.5849, 0.8464]),
      "F":np.array([5.6169, 1.0816, 0.5041]),
      "A":np.array([3.1329, 0.3249, 3.2400]),
      "SA":np.array([5.2441, 2.0736, 4.1616]),
      "SU": np.array([0.2500, 6.2500, 10.1761]),
      "D": np.array([5.1529, 0.0484, 0.1849]),
      "N": np.array([0.3364, 0.5625, 0.3136]),
      "B": np.array([3.4225, 0.7396, 4.0401])
    }

    self.emotionShow = rospy.ServiceProxy('/qt_robot/emotion/show', emotion_show)
    self.emotionStop = rospy.ServiceProxy('/qt_robot/emotion/stop', emotion_stop)
    self.audioPlay = rospy.ServiceProxy('/qt_robot/audio/play', audio_play)
    self.gesturePlay = rospy.ServiceProxy('/qt_robot/gesture/play', gesture_play)
    self.talkText = rospy.ServiceProxy('/qt_robot/behavior/talkText', behavior_talk_text)
    self.speechConfig = rospy.ServiceProxy('/qt_robot/speech/config', speech_config)
    self.setVolume = rospy.ServiceProxy('/qt_robot/setting/setVolume', setting_setVolume)
    self.recognizeQuestion = rospy.ServiceProxy('/qt_robot/speech/recognize', speech_recognize)
    self.emotionConverter = rospy.ServiceProxy('/emotion_converter', EmotionConverter)
    self.emotion_pub = rospy.Publisher('/qt_robot/emotion/show', String, queue_size=10)
    self.user_res_pub = rospy.Publisher('/qt_robot/user_response', String, queue_size=10)

    self.face_sub = rospy.Subscriber('/qt_nuitrack_app/faces', Faces, self.face_callback)

    self.wait_services()
    self.configure_voice()


  def wait_services(self):
    services = [
        '/qt_robot/emotion/show',
        '/qt_robot/emotion/stop',
        '/qt_robot/audio/play',
        '/qt_robot/gesture/play',
        '/qt_robot/behavior/talkText',
        '/qt_robot/speech/config',
        '/qt_robot/setting/setVolume',
        '/qt_robot/speech/recognize',
        'emotion_converter',
    ]
    threads = [threading.Thread(target=rospy.wait_for_service, args=(s,)) for s in services]
    for t in threads: t.start()
    for t in threads: t.join()


  def configure_voice(self):
    self.speechConfig(language=self.tts_voice, pitch=115, speed=102)
    self.setVolume(80)


  def hide_image(self):
    try:
        self.emotionStop()
    except rospy.ServiceException as e:
        rospy.logerr(f"Errore nell'emotion stop: {e}")


  def listen(self, image=None):
    try:
        if image is not None:
            self.show_image(image)
        result = self.recognizeQuestion(language='it_IT', options='', timeout=0)
        if image is not None:
            self.hide_image()

        if result and result.transcript:
            rospy.loginfo(f"Riconosciuto: {result.transcript}")
            return result.transcript
        return None
    except Exception as e:
        if image is not None:
            self.hide_image()
        rospy.logerr(f"Errore nel riconoscimento vocale: {e}")
        return None

  def check_repeat_request(self, transcript):
    t = transcript.lower().strip()
    if any(trigger in t for trigger in self.REPEAT_TRIGGERS):
        return True
    repeat_keywords = ["ripet", "capito", "sentito", "cosa", "eh"]
    return any(keyword in t for keyword in repeat_keywords)


  def check_yes_no(self, transcript):
    if transcript is None:
        return None
    t = transcript.lower().strip()
    if any(trigger in t for trigger in self.YES_TRIGGERS):
        return 1
    if any(trigger in t for trigger in self.NO_TRIGGERS):
        return 0
    return None


  def play_sound(self, filename):
    try:
      rospy.loginfo(f"Riproduzione suono: {filename}")
      self.audioPlay(filename=filename)
      return True
    except rospy.ServiceException as e:
      rospy.logerr(f"Errore nella riproduzione audio: {e}")
      return False


  def show_image(self, filename):
      rospy.loginfo(f"Mostro immagine: {filename}")
      self.emotion_pub.publish(filename)


  def get_emotion(self, emotion_label):
    try:
      response = self.emotionConverter(label=emotion_label)
      if response.success:
        return True, response.epa, response.epa_squared
      else:
        rospy.logwarn(f"Label emozione non riconosciuta: {emotion_label}")
        return False, response.epa, response.epa_squared
    except rospy.ServiceException as e:
      rospy.logerr(f"Chiamata al servizio emotion_converter fallita: {e}")
      return False, [], []


  def face_callback(self, msg):
    if not msg.faces:
        self.is_face_visible = False
        return

    self.is_face_visible = True
    face = msg.faces[0]

    emotions = [face.emotion_angry, face.emotion_happy, face.emotion_surprise]
    em = max(emotions)
    em_index = emotions.index(em)

    if em >= 0.9:
        if em_index == 0:
            self.current_user_emotion = "A"
        elif em_index == 1:
            self.current_user_emotion = "H"
        elif em_index == 2:
            self.current_user_emotion = "SU"


  def wait_and_get_user_emotion(self):
    rospy.loginfo("In attesa di un'emozione forte (>= 0.9) da parte dell'utente...")
    self.current_user_emotion = None

    rate = rospy.Rate(10)
    while not rospy.is_shutdown():
        if self.is_face_visible and self.current_user_emotion is not None:
            rospy.loginfo(f"Espressione chiara rilevata! Etichetta: {self.current_user_emotion}")
            return self.current_user_emotion
        rate.sleep()

    return "N"