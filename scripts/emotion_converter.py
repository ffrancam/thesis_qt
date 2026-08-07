#!/usr/bin/env python3
import rospy
import numpy as np

from thesis_qt.srv import EmotionConverter, EmotionConverterResponse

class EmotionConverterServer:
  def __init__(self):
    # Emotion dictionary to assign a static epa value to each emotion
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

    # Emotion dictionary for squared value of each epa
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

    # Initialize ROS node
    rospy.init_node('emotion_converter_srv_node')

    # Create service
    self.srv = rospy.Service('emotion_converter', EmotionConverter, self.handle_get_epa)
    rospy.loginfo("Emotion converter service initialized succesfully.")
  
  def handle_get_epa(self, req):
    # Get request
    label = req.label.strip().upper()

    # Prepare response
    res = EmotionConverterResponse()

    if label in self.emotion_map:
      epa = self.emotion_map[label]
      epa_squared = self.emotion_map_squared[label]

      res.success = True
      # Converter for ROS1
      res.epa = epa.tolist()
      res.epa_squared = epa_squared.tolist()

      rospy.loginfo("EPA computed.")
    else:
      res.success = False
      res.epa =[0.0, 0.0, 0.0]
      res.epa_squared = [0.0, 0.0, 0.0]
      rospy.loginfo("Unknow label.")
    
    return res


if __name__ == '__main__':
  try:
    server = EmotionConverterServer()

    rospy.spin()
  except rospy.ROSInterruptException:
    pass
