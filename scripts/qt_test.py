#!/usr/bin/env python3

import rospy
import shutil
import rospkg
from rosplan_knowledge_msgs.srv import *
from rosplan_knowledge_msgs.msg import KnowledgeItem
from diagnostic_msgs.msg import KeyValue
from std_srvs.srv import Empty
import random


class QTRobotROSPlanTest:
    def __init__(self):
        rospy.init_node('qt_test_node')

        # Percorsi file
        rospack = rospkg.RosPack()
        self.pkg_path = rospack.get_path('thesis_qt')
        self.domain_path = self.pkg_path + '/pddl/domain_try.pddl'
        self.domain_backup_path = self.pkg_path + '/pddl/domain_try_backup.pddl'
        self.problem_path = self.pkg_path + '/pddl/problem_try.pddl'

        # Backup del dominio PRIMA di fare qualsiasi cosa
        shutil.copyfile(self.domain_path, self.domain_backup_path)
        print(f"✓ Domain backup saved to: {self.domain_backup_path}")

        print("Waiting for ROSPlan services...")
        rospy.wait_for_service('/rosplan_knowledge_base/clear')
        rospy.wait_for_service('/rosplan_knowledge_base/update')
        rospy.wait_for_service('/rosplan_problem_interface/problem_generation_server')
        rospy.wait_for_service('/rosplan_planner_interface/planning_server')
        rospy.wait_for_service('/rosplan_parsing_interface/parse_plan')

        self.clear_kb = rospy.ServiceProxy('/rosplan_knowledge_base/clear', Empty)
        self.update_kb = rospy.ServiceProxy('/rosplan_knowledge_base/update', KnowledgeUpdateService)
        self.generate_problem = rospy.ServiceProxy('/rosplan_problem_interface/problem_generation_server', Empty)
        self.plan = rospy.ServiceProxy('/rosplan_planner_interface/planning_server', Empty)
        self.parse_plan = rospy.ServiceProxy('/rosplan_parsing_interface/parse_plan', Empty)

        print("ROSPlan services ready!")

    def add_function(self, function_name, params, value):
        knowledge = KnowledgeItem()
        knowledge.knowledge_type = KnowledgeItem.FUNCTION
        knowledge.attribute_name = function_name

        for key, val in params:
            knowledge.values.append(KeyValue(key, val))

        knowledge.function_value = float(value)

        req = KnowledgeUpdateServiceRequest()
        req.update_type = KnowledgeUpdateServiceRequest.ADD_KNOWLEDGE
        req.knowledge = knowledge

        response = self.update_kb(req)
        if response.success:
            print(f"  ✓ Function: {function_name} = {value}")
        else:
            print(f"  ✗ Failed: {function_name}")
        return response.success

    def add_fact(self, predicate_name, params):
        knowledge = KnowledgeItem()
        knowledge.knowledge_type = KnowledgeItem.FACT
        knowledge.attribute_name = predicate_name
        knowledge.is_negative = False

        for key, value in params:
            knowledge.values.append(KeyValue(key, value))

        req = KnowledgeUpdateServiceRequest()
        req.update_type = KnowledgeUpdateServiceRequest.ADD_KNOWLEDGE
        req.knowledge = knowledge

        response = self.update_kb(req)
        if response.success:
            print(f"  ✓ Fact: {predicate_name}")
        else:
            print(f"  ✗ Failed fact: {predicate_name}")
        return response.success

    def add_goal(self, predicate_name, params):
        knowledge = KnowledgeItem()
        knowledge.knowledge_type = KnowledgeItem.FACT
        knowledge.attribute_name = predicate_name
        knowledge.is_negative = False

        for key, value in params:
            knowledge.values.append(KeyValue(key, value))

        req = KnowledgeUpdateServiceRequest()
        req.update_type = KnowledgeUpdateServiceRequest.ADD_GOAL
        req.knowledge = knowledge

        response = self.update_kb(req)
        if response.success:
            print(f"  ✓ Goal: {predicate_name}")
        else:
            print(f"  ✗ Failed goal: {predicate_name}")
        return response.success

    def restore_domain(self):
        shutil.copyfile(self.domain_backup_path, self.domain_path)
        print("✓ Domain restored from backup.")

    def patch_problem_metric(self):
        with open(self.problem_path, 'r') as f:
            content = f.read()

        if '(:metric' not in content:
            content = content.rstrip().rstrip(')')
            content += '\n(:metric minimize (total-cost))\n)\n'
            with open(self.problem_path, 'w') as f:
                f.write(content)
            print("✓ Metric added to problem file.")
        else:
            print("✓ Metric already present in problem file.")

    def setup_problem(self):
        print("\n=== Clearing Knowledge Base ===")
        self.clear_kb()
        print("✓ Knowledge Base cleared.")

        # Nessun fatto iniziale: interaction_started, quiz_introduced, ecc.
        # vengono tutti raggiunti tramite le azioni del piano.
        # L'unico fatto che NON deve essere settato è emotion_checked
        # (il dominio parte senza di esso e lo acquisisce con check_emotion).

        self.add_fact('interaction_started', [])

        # Funzioni robot
        print("\n=== Adding robot functions ===")
        self.add_function('robot_e',    [], 3.44)
        self.add_function('robot_p',    [], 2.93)
        self.add_function('robot_a',    [], 0.92)
        self.add_function('robot_e_sq', [], 11.8336)
        self.add_function('robot_p_sq', [], 8.5849)
        self.add_function('robot_a_sq', [], 0.8464)
        # self.add_function('robot_e',    [], -2.29)
        # self.add_function('robot_p',    [], -1.44)
        # self.add_function('robot_a',    [], -2.04)
        # self.add_function('robot_e_sq', [], 5.2441)
        # self.add_function('robot_p_sq', [], 2.0736)
        # self.add_function('robot_a_sq', [], 4.1616)

        # Funzioni human
        print("\n=== Adding human functions ===")
        self.add_function('human_e',    [], 3.44)
        self.add_function('human_p',    [], 2.93)
        self.add_function('human_a',    [], 0.92)
        self.add_function('human_e_sq', [], 11.8336)
        self.add_function('human_p_sq', [], 8.5849)
        self.add_function('human_a_sq', [], 0.8464)
        # self.add_function('human_e',    [], -2.27)
        # self.add_function('human_p',    [], 0.22)
        # self.add_function('human_a',    [], 0.43)
        # self.add_function('human_e_sq', [], 5.1529)
        # self.add_function('human_p_sq', [], 0.0484)
        # self.add_function('human_a_sq', [], 0.1849)

        # Pesi
        print("\n=== Adding weights ===")
        self.add_function('alpha',      [], 1.0)
        self.add_function('beta',       [], 1.0)
        self.add_function('gamma',      [], 1.0)
        self.add_function('total-cost', [], 0.0)

        # Stato quiz
        print("\n=== Adding quiz state ===")
        self.add_function('difficulty_limit', [], 1.0)  # ogni livello max 2 volte (< 2)
        self.add_function('category_limit', [], 1.0)  # contatore livello corrente
        self.add_function('category_limit_bonus', [], 2.0)
        self.add_function('right_answers',    [], 0.0)
        self.add_function('wrong_answers',    [], 0.0)
        self.add_function('n_questions',      [], 0.0)
        self.add_function('n_easy',           [], 0.0)
        self.add_function('n_medium',         [], 0.0)
        self.add_function('n_hard',           [], 0.0)
        self.add_function('ask_uses',            [], 0.0)
        self.add_function('mime_uses',           [], 0.0)
        self.add_function('sound_uses',          [], 0.0)
        self.add_function('image_uses',          [], 0.0)

        # Coefficienti modalità
        print("\n=== Adding modality coefficients ===")
        modalities = ['ask', 'mime', 'sound', 'image']
        random.shuffle(modalities)  # Shuffle iniziale: una modalità parte favorita, le altre penalizzate
        initial_costs = [1.0, 20.0, 40.0, 60.0] # Assegna costi iniziali scalati: primo=base, poi crescente

        for modality, cost in zip(modalities, initial_costs):
            # if modality == 'mime':
            #     self.add_function(f'{modality}_coeff', [], 1111.0)  # Mime sempre sfavorito
            # else:
            self.add_function(f'{modality}_coeff', [], cost)


        # Coefficienti per livello
        print("\n=== Adding difficulty-level coefficients ===")
        self.add_function('sound_easy_coeff',   [], 1.0)
        self.add_function('sound_medium_coeff', [], 1.0)
        self.add_function('sound_hard_coeff',   [], 1.0)
        self.add_function('image_easy_coeff',   [], 1.0)
        self.add_function('image_medium_coeff', [], 1.0)
        self.add_function('image_hard_coeff',   [], 1.0)
        self.add_function('ask_easy_coeff',     [], 1.0)
        self.add_function('ask_medium_coeff',   [], 1.0)
        self.add_function('ask_hard_coeff',     [], 1.0)
        self.add_function('mime_easy_coeff',    [], 1.0)

        # Goal
        print("\n=== Adding goal ===")
        self.add_goal('interaction_finished', [])

    def run_planning(self):
        print("\n=== Generating problem ===")
        self.generate_problem()

        print("\n=== Restoring domain ===")
        self.restore_domain()

        print("\n=== Patching problem metric ===")
        self.patch_problem_metric()

        print("\n=== Planning (ENHSP) ===")
        try:
            self.plan()
        except rospy.ServiceException as e:
            print(f"Planning failed: {e}")

        print("\n=== Parsing plan ===")
        try:
            self.parse_plan()
        except rospy.ServiceException as e:
            print(f"Parsing failed: {e}")

        print("\n=== Plan ready! ===")


def main():
    try:
        test = QTRobotROSPlanTest()
        test.setup_problem()
        test.run_planning()

        print("\n✓ Planning pipeline executed!")
        print("To dispatch: rosservice call /rosplan_plan_dispatcher/dispatch_plan")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()