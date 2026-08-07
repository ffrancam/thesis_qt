#!/usr/bin/env python3

import rospy
import wave
import os
from audio_common_msgs.msg import AudioData

class AudioRecorder:
    def __init__(self):
        rospy.init_node('audio_recorder_node')

        # Percorso di salvataggio: home dell'utente, facile da trovare
        save_dir = os.path.expanduser('~/qt_recordings')
        os.makedirs(save_dir, exist_ok=True)
        self.filepath = os.path.join(save_dir, 'audio.wav')

        self.wf = wave.open(self.filepath, 'wb')
        self.wf.setnchannels(1)
        self.wf.setsampwidth(2)   # 16 bit
        self.wf.setframerate(16000)

        rospy.Subscriber('/qt_respeaker_app/channel0', AudioData, self.callback)

        # Chiusura pulita anche con Ctrl+C
        rospy.on_shutdown(self.shutdown)

        rospy.loginfo(f"Recording started, saving to {self.filepath}")
        rospy.loginfo("Press Ctrl+C to stop recording.")

    def callback(self, msg):
        self.wf.writeframes(msg.data)

    def shutdown(self):
        self.wf.close()
        rospy.loginfo(f"Recording saved: {self.filepath}")

if __name__ == '__main__':
    try:
        AudioRecorder()
        rospy.spin()
    except rospy.ROSInterruptException:
        pass