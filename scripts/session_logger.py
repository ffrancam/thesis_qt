#!/usr/bin/env python3
"""
session_logger.py
-----------------
Nodo ROS che crea una cartella di sessione e salva automaticamente:
  - il piano iniziale (plan_0.txt)
  - i piani generati dopo ogni replan (plan_1.txt, plan_2.txt, …)
  - i problemi PDDL generati ad ogni replan (problem_1.pddl, …)
  - un log continuo degli action dispatch / feedback (dispatch.log)
  - uno snapshot delle variabili KB all'avvio e dopo ogni replan (kb_snapshot_N.json)

Utilizzo nel launch:
    <node pkg="thesis_qt" type="session_logger.py" name="session_logger_node"
          output="screen">
        <param name="session_name" value="$(arg session_name)" />
    </node>
"""

import os
import json
import shutil
import threading
from datetime import datetime

import rospy
import rospkg
from std_msgs.msg import String
from rosplan_dispatch_msgs.msg import ActionDispatch, ActionFeedback
from rosplan_knowledge_msgs.srv import GetAttributeService


# ─────────────────────────────────────────────────────────────────────────────

class SessionLogger:

    def __init__(self):
        rospy.init_node('session_logger_node')

        # ── Cartella di sessione ──────────────────────────────────────────────
        session_name = rospy.get_param('~session_name', '')
        if not session_name:
            session_name = datetime.now().strftime('session_%Y%m%d_%H%M%S')

        rospack = rospkg.RosPack()
        pkg_path = rospack.get_path('thesis_qt')
        self.session_dir = os.path.join(pkg_path, 'logs', session_name)
        os.makedirs(self.session_dir, exist_ok=True)

        self.problem_path = os.path.join(pkg_path, 'pddl', 'problem_try.pddl')

        rospy.loginfo(f"[SessionLogger] Session directory: {self.session_dir}")

        # ── Contatori ─────────────────────────────────────────────────────────
        self._plan_count    = 0   # 0 = piano iniziale
        self._replan_count  = 0   # incrementato a ogni replan
        self._lock          = threading.Lock()

        # ── File di log continuo ──────────────────────────────────────────────
        self._dispatch_log = open(
            os.path.join(self.session_dir, 'dispatch.log'), 'w', buffering=1
        )
        self._write_dispatch(f"=== Session: {session_name}  started at {datetime.now()} ===\n")

        # ── Aspetta i servizi KB (opzionale, con timeout) ─────────────────────
        try:
            rospy.wait_for_service('/rosplan_knowledge_base/state/functions', timeout=30)
            rospy.wait_for_service('/rosplan_knowledge_base/state/predicates', timeout=30)
            self.get_functions  = rospy.ServiceProxy('/rosplan_knowledge_base/state/functions',  GetAttributeService)
            self.get_predicates = rospy.ServiceProxy('/rosplan_knowledge_base/state/predicates', GetAttributeService)
            self._kb_available = True
        except rospy.ROSException:
            rospy.logwarn("[SessionLogger] KB services not available – KB snapshots disabled.")
            self._kb_available = False

        # ── Subscriber ────────────────────────────────────────────────────────
        rospy.Subscriber('/rosplan_planner_interface/planner_output',
                         String, self._on_plan)

        rospy.Subscriber('/rosplan_plan_dispatcher/action_dispatch',
                         ActionDispatch, self._on_dispatch)

        rospy.Subscriber('/rosplan_plan_dispatcher/action_feedback',
                         ActionFeedback, self._on_feedback)

        # ── Snapshot iniziale KB ──────────────────────────────────────────────
        rospy.Timer(rospy.Duration(3.0), self._initial_snapshot, oneshot=True)

        rospy.loginfo("[SessionLogger] Ready.")
        rospy.spin()

        self._dispatch_log.close()

    # ── Callbacks ─────────────────────────────────────────────────────────────

    def _on_plan(self, msg: String):
        """Salva ogni piano pubblicato sul topic del planner."""
        with self._lock:
            idx = self._plan_count
            self._plan_count += 1

        filename = f"plan_{idx}.txt"
        filepath = os.path.join(self.session_dir, filename)
        with open(filepath, 'w') as f:
            f.write(f"# Plan #{idx}  –  {datetime.now()}\n")
            f.write(msg.data)
            f.write('\n')

        label = "initial plan" if idx == 0 else f"replan #{idx}"
        rospy.loginfo(f"[SessionLogger] Saved {label} → {filename}")

        # Se è un replan, salva anche il problema PDDL corrente
        if idx > 0:
            self._save_problem(idx)
            self._save_kb_snapshot(idx)

    def _on_dispatch(self, msg: ActionDispatch):
        params = ', '.join(f"{p.key}={p.value}" for p in msg.parameters)
        line = f"[{datetime.now().strftime('%H:%M:%S')}] DISPATCH  id={msg.action_id:3d}  {msg.name}({params})\n"
        self._write_dispatch(line)

    def _on_feedback(self, msg: ActionFeedback):
        status_map = {
            ActionFeedback.ACTION_ENABLED:                  'ENABLED',
            ActionFeedback.ACTION_SUCCEEDED_TO_GOAL_STATE:  'SUCCEEDED ✓',
            ActionFeedback.ACTION_FAILED:                   'FAILED ✗',
        }
        status = status_map.get(msg.status, f'STATUS_{msg.status}')
        line = f"[{datetime.now().strftime('%H:%M:%S')}] FEEDBACK  id={msg.action_id:3d}  {status}\n"
        self._write_dispatch(line)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _write_dispatch(self, text: str):
        try:
            self._dispatch_log.write(text)
        except Exception as e:
            rospy.logwarn(f"[SessionLogger] Could not write dispatch log: {e}")

    def _save_problem(self, idx: int):
        """Copia il file problem_try.pddl corrente nella cartella di sessione."""
        if not os.path.exists(self.problem_path):
            rospy.logwarn(f"[SessionLogger] Problem file not found: {self.problem_path}")
            return
        dest = os.path.join(self.session_dir, f"problem_{idx}.pddl")
        shutil.copy2(self.problem_path, dest)
        rospy.loginfo(f"[SessionLogger] Saved problem → problem_{idx}.pddl")

    def _save_kb_snapshot(self, idx: int):
        """Salva uno snapshot JSON delle funzioni e predicati correnti della KB."""
        if not self._kb_available:
            return
        snapshot = self._collect_kb()
        if snapshot is None:
            return
        dest = os.path.join(self.session_dir, f"kb_snapshot_{idx}.json")
        with open(dest, 'w') as f:
            json.dump(snapshot, f, indent=2)
        rospy.loginfo(f"[SessionLogger] Saved KB snapshot → kb_snapshot_{idx}.json")

    def _initial_snapshot(self, _event):
        """Snapshot KB allo startup (indice 0)."""
        self._save_kb_snapshot(0)

    def _collect_kb(self):
        """Interroga la KB e restituisce un dict con funzioni e predicati."""
        try:
            funcs = self.get_functions('')
            preds = self.get_predicates('')

            functions = {
                item.attribute_name: item.function_value
                for item in funcs.attributes
            }

            predicates = []
            for item in preds.attributes:
                entry = {'name': item.attribute_name}
                if item.values:
                    entry['params'] = {kv.key: kv.value for kv in item.values}
                predicates.append(entry)

            return {
                'timestamp': datetime.now().isoformat(),
                'functions': functions,
                'predicates': predicates,
            }
        except Exception as e:
            rospy.logwarn(f"[SessionLogger] KB collection failed: {e}")
            return None


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    try:
        SessionLogger()
    except rospy.ROSInterruptException:
        pass