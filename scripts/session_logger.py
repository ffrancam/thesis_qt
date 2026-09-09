#!/usr/bin/env python3
"""
session_logger.py
"""

import os
import json
import shutil
import threading
from datetime import datetime

import rospy
import rospkg
from std_msgs.msg import String
from rosgraph_msgs.msg import Log
from rosplan_dispatch_msgs.msg import ActionDispatch, ActionFeedback
from rosplan_knowledge_msgs.srv import GetAttributeService


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

        if os.path.exists(self.session_dir):
            shutil.rmtree(self.session_dir)
        os.makedirs(self.session_dir)

        self.problem_path = os.path.join(pkg_path, 'pddl', 'problem_try.pddl')

        rospy.loginfo(f"[SessionLogger] Session directory: {self.session_dir}")

        # ── Contatori ─────────────────────────────────────────────────────────
        self._plan_count   = 0
        self._replan_count = 0
        self._lock         = threading.Lock()

        # ── File di log continuo ──────────────────────────────────────────────
        self._dispatch_log = open(
            os.path.join(self.session_dir, 'dispatch.log'), 'w', buffering=1
        )
        self._write_dispatch(f"=== Session: {session_name}  started at {datetime.now()} ===\n")

        # ── Log per nodo action / evaluator ───────────────────────────────────
        self._action_logs = {}
        self._action_lock = threading.Lock()

        # ── Timer sessione ────────────────────────────────────────────────────
        self._timer_start = None
        self._id_to_name  = {}
        self._timer_file  = os.path.join(self.session_dir, 'session_timer.log')

        # ── Timer replan ──────────────────────────────────────────────────────
        self._replan_start = None  # timestamp inizio replan

        # ── KB ────────────────────────────────────────────────────────────────
        self.get_functions  = None
        self.get_predicates = None
        self._kb_available  = False
        self._try_connect_kb()

        # ── Subscriber ────────────────────────────────────────────────────────
        rospy.Subscriber('/rosplan_planner_interface/planner_output',
                         String, self._on_plan)
        rospy.Subscriber('/rosplan_plan_dispatcher/action_dispatch',
                         ActionDispatch, self._on_dispatch)
        rospy.Subscriber('/rosplan_plan_dispatcher/action_feedback',
                         ActionFeedback, self._on_feedback)
        rospy.Subscriber('/rosout_agg', Log, self._on_rosout)

        # ── Snapshot iniziale KB ──────────────────────────────────────────────
        rospy.Timer(rospy.Duration(3.0), self._initial_snapshot, oneshot=True)

        rospy.loginfo("[SessionLogger] Ready.")
        rospy.spin()

        self._dispatch_log.close()
        for f in self._action_logs.values():
            f.close()

    # ── Callbacks ─────────────────────────────────────────────────────────────

    def _on_plan(self, msg: String):
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

        if idx > 0:
            # ── Chiudi timer replan ───────────────────────────────────────────
            if self._replan_start is not None:
                end   = datetime.now()
                delta = end - self._replan_start
                secs  = delta.total_seconds()
                self._write_timer(
                    f"[{end.strftime('%H:%M:%S')}] REPLAN #{idx} DONE\n"
                    f"  Tempo ripianificazione: {secs:.2f}s\n"
                )
                self._replan_start = None

            self._save_problem(idx)
            self._save_kb_snapshot(idx)
        else:
            # ── Primo piano: nessun replan timer ─────────────────────────────
            pass

    def _on_dispatch(self, msg: ActionDispatch):
        params = ', '.join(f"{p.key}={p.value}" for p in msg.parameters)
        line = f"[{datetime.now().strftime('%H:%M:%S')}] DISPATCH  id={msg.action_id:3d}  {msg.name}({params})\n"
        self._write_dispatch(line)

        # Mappa id → nome per usarla in _on_feedback
        self._id_to_name[msg.action_id] = msg.name

        # Avvia timer sessione quando parte greet_warmly
        if msg.name == 'greet_warmly':
            self._timer_start = datetime.now()
            self._write_timer(
                f"[{self._timer_start.strftime('%H:%M:%S')}] TIMER START — greet_warmly\n"
            )

    def _on_feedback(self, msg: ActionFeedback):
        status_map = {
            ActionFeedback.ACTION_ENABLED:                 'ENABLED',
            ActionFeedback.ACTION_SUCCEEDED_TO_GOAL_STATE: 'SUCCEEDED ✓',
            ActionFeedback.ACTION_FAILED:                  'FAILED ✗',
        }
        status = status_map.get(msg.status, f'STATUS_{msg.status}')
        line = f"[{datetime.now().strftime('%H:%M:%S')}] FEEDBACK  id={msg.action_id:3d}  {status}\n"
        self._write_dispatch(line)

        action_name = self._id_to_name.get(msg.action_id, '')
        is_terminal = msg.status in (
            ActionFeedback.ACTION_SUCCEEDED_TO_GOAL_STATE,
            ActionFeedback.ACTION_FAILED,
        )

        # Stoppa timer sessione su conclude_game o raise_stakes
        if action_name in ('conclude_game', 'raise_stakes') and is_terminal:
            if self._timer_start:
                end   = datetime.now()
                delta = end - self._timer_start
                total = str(delta).split('.')[0]
                self._write_timer(
                    f"[{end.strftime('%H:%M:%S')}] TIMER STOP  — {action_name}\n"
                    f"  Durata sessione: {total}\n"
                )
                self._timer_start = None

        # Avvia timer replan quando un'azione fallisce
        if msg.status == ActionFeedback.ACTION_FAILED:
            self._replan_start = datetime.now()
            with self._lock:
                replan_idx = self._plan_count  # il prossimo piano che arriverà
            self._write_timer(
                f"[{self._replan_start.strftime('%H:%M:%S')}] REPLAN #{replan_idx} START"
                f" — triggered by '{action_name}' FAILED\n"
            )

    def _on_rosout(self, msg: Log):
        is_action    = 'action' in msg.name
        is_evaluator = 'evaluator' in msg.name
        if not is_action and not is_evaluator:
            return

        level_map = {
            Log.DEBUG: 'DEBUG',
            Log.INFO:  'INFO ',
            Log.WARN:  'WARN ',
            Log.ERROR: 'ERROR',
            Log.FATAL: 'FATAL',
        }
        level = level_map.get(msg.level, f'LVL{msg.level}')
        line  = f"[{datetime.fromtimestamp(msg.header.stamp.to_sec()).strftime('%H:%M:%S')}] [{level}] {msg.msg}\n"

        with self._action_lock:
            if msg.name not in self._action_logs:
                filepath = os.path.join(self.session_dir, f"{msg.name.strip('/')}.log")
                self._action_logs[msg.name] = open(filepath, 'w', buffering=1)
            self._action_logs[msg.name].write(line)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _write_dispatch(self, text: str):
        try:
            self._dispatch_log.write(text)
        except Exception as e:
            rospy.logwarn(f"[SessionLogger] Could not write dispatch log: {e}")

    def _write_timer(self, text: str):
        with open(self._timer_file, 'a') as f:
            f.write(text)

    def _try_connect_kb(self):
        try:
            rospy.wait_for_service('/rosplan_knowledge_base/state/functions', timeout=5)
            rospy.wait_for_service('/rosplan_knowledge_base/state/predicates', timeout=5)
            self.get_functions  = rospy.ServiceProxy('/rosplan_knowledge_base/state/functions',  GetAttributeService)
            self.get_predicates = rospy.ServiceProxy('/rosplan_knowledge_base/state/predicates', GetAttributeService)
            self._kb_available  = True
            rospy.loginfo("[SessionLogger] KB services connected.")
        except rospy.ROSException:
            rospy.logwarn("[SessionLogger] KB not ready yet, will retry at first snapshot.")

    def _save_problem(self, idx: int):
        if not os.path.exists(self.problem_path):
            rospy.logwarn(f"[SessionLogger] Problem file not found: {self.problem_path}")
            return
        dest = os.path.join(self.session_dir, f"problem_{idx}.pddl")
        shutil.copy2(self.problem_path, dest)
        rospy.loginfo(f"[SessionLogger] Saved problem → problem_{idx}.pddl")

    def _save_kb_snapshot(self, idx: int):
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
        self._save_kb_snapshot(0)

    def _collect_kb(self):
        if not self._kb_available:
            self._try_connect_kb()
        if not self._kb_available:
            return None
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


if __name__ == '__main__':
    try:
        SessionLogger()
    except rospy.ROSInterruptException:
        pass