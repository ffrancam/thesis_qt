#!/usr/bin/env python3

import rospy
import subprocess
import re
import os
from std_srvs.srv import Empty, EmptyResponse
from std_msgs.msg import String

class ENHSPPlannerInterface:
    def __init__(self):
        rospy.init_node('enhsp_planner_interface')
        
        # Parametri
        self.domain_path = rospy.get_param('~domain_path')
        self.problem_path = rospy.get_param('~problem_path')
        self.data_path = rospy.get_param('~data_path', '/tmp/')
        self.search_algorithm = rospy.get_param('~search_algorithm', 'WAStar')
        self.heuristic = rospy.get_param('~heuristic', 'hadd')
        
        # Path a ENHSP
        package_path = os.popen("rospack find thesis_qt").read().strip()
        self.enhsp_jar = os.path.join(package_path, "planners/ENHSP-Public/enhsp-dist/enhsp.jar")
        
        # Publisher per il piano
        self.plan_pub = rospy.Publisher('/rosplan_planner_interface/planner_output', 
                                       String, queue_size=1, latch=True)
        
        # Service
        self.planning_service = rospy.Service('/rosplan_planner_interface/planning_server',
                                             Empty, self.planning_callback)
        
        rospy.loginfo("ENHSP Planner Interface ready!")
        rospy.spin()
    
    def planning_callback(self, req):
        """Callback del servizio di planning"""
        rospy.loginfo("Planning request received...")
        
        try:
            # Esegui ENHSP
            cmd = [
                'java', '-jar', self.enhsp_jar,
                '-o', self.domain_path,
                '-f', self.problem_path,
                '-s', self.search_algorithm,
                '-h', self.heuristic
            ]
            
            rospy.loginfo(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            # Log dell'output completo per debug
            rospy.loginfo("ENHSP output:")
            rospy.loginfo(result.stdout)
            
            if result.returncode != 0:
                rospy.logerr(f"ENHSP failed: {result.stderr}")
                return EmptyResponse()

            # try:
            #     # Creiamo il percorso completo del file
            #     raw_plan_file = os.path.join(self.data_path, "qt_test_plan.txt")
                
            #     # Apriamo il file in modalità scrittura ('w')
            #     with open(raw_plan_file, 'w') as f:
            #         f.write(result.stdout)
                    
            #     rospy.loginfo(f"Raw ENHSP plan successfully saved to: {raw_plan_file}")
            # except Exception as e:
            #     rospy.logwarn(f"Failed to save raw plan to file: {e}")
            
            # Parse dell'output di ENHSP
            plan = self.parse_enhsp_output(result.stdout)
            
            if plan:
                rospy.loginfo(f"Plan found with  {len(plan.split(chr(10)))} actions")
                # Pubblica il piano nel formato POPF
                self.plan_pub.publish(plan)
            else:
                rospy.logwarn("No plan found in ENHSP output")
            
            return EmptyResponse()
            
        except subprocess.TimeoutExpired:
            rospy.logerr("ENHSP timeout!")
            return EmptyResponse()
        except Exception as e:
            rospy.logerr(f"Error running ENHSP: {e}")
            import traceback
            traceback.print_exc()
            return EmptyResponse()
    
    def parse_enhsp_output(self, output):
        """
        Converte l'output di ENHSP nel formato POPF
        
        ENHSP output:
        0.0: (goto_location robot1 loc_a loc_b)
        1.0: (goto_location robot1 loc_b loc_c)
        
        POPF format:
        0.000: (goto_location robot1 loc_a loc_b)  [0.001]
        0.001: (goto_location robot1 loc_b loc_c)  [0.001]
        """
        lines = output.split('\n')
        plan_lines = []
        in_plan = False
        
        for line in lines:
            # Cerca "Found Plan:" per iniziare
            if "Found Plan:" in line:
                in_plan = True
                continue
            
            # Fermati a fine piano
            if in_plan and ("Plan-Length:" in line or "Metric" in line):
                break
            
            # Estrai le azioni
            if in_plan:
                # Match: "0.0: (goto_location robot1 loc_a loc_b)"
                match = re.match(r'(\d+\.?\d*)\s*:\s*(\(.*\))', line.strip())
                if match:
                    time = float(match.group(1))
                    action = match.group(2)
                    # Converti in formato POPF con durata di default 0.001
                    popf_line = f"{time:.3f}: {action}  [0.001]"
                    plan_lines.append(popf_line)
        
        if plan_lines:
            return '\n'.join(plan_lines)
        else:
            return None

if __name__ == '__main__':
    try:
        ENHSPPlannerInterface()
    except rospy.ROSInterruptException:
        pass
