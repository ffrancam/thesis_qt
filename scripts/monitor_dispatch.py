#!/usr/bin/env python3

import rospy
from rosplan_dispatch_msgs.msg import ActionDispatch, ActionFeedback

class DispatchMonitor:
    def __init__(self):
        rospy.init_node('dispatch_monitor')
        
        self.actions = {}
        
        rospy.Subscriber('/rosplan_plan_dispatcher/action_dispatch',
                        ActionDispatch, self.dispatch_callback)
        rospy.Subscriber('/rosplan_plan_dispatcher/action_feedback',
                        ActionFeedback, self.feedback_callback)
        
        print("Monitoring plan execution...")
        print("=" * 50)
        rospy.spin()
    
    def dispatch_callback(self, msg):
        """Nuova azione dispatched"""
        self.actions[msg.action_id] = {
            'name': msg.name,
            'params': {p.key: p.value for p in msg.parameters},
            'status': 'DISPATCHED'
        }
        
        params_str = ', '.join([f"{k}={v}" for k, v in self.actions[msg.action_id]['params'].items()])
        print(f"\n[{msg.action_id}] DISPATCHED: {msg.name}({params_str})")
    
    def feedback_callback(self, msg):
        """Feedback ricevuto"""
        if msg.action_id not in self.actions:
            self.actions[msg.action_id] = {'name': 'unknown', 'params': {}}
        
        # Status map con le costanti corrette
        status_map = {
            0: "ACTION_ENABLED",
            1: "ACTION_DISPATCHED",
            2: "? ACTION_SUCCEEDED",
            3: "? ACTION_FAILED",
        }
        
        # Usa il valore numerico direttamente se le costanti non sono definite
        try:
            status = status_map.get(msg.status, f"UNKNOWN({msg.status})")
        except:
            status = f"STATUS_{msg.status}"
        
        self.actions[msg.action_id]['status'] = status
        
        action = self.actions[msg.action_id]
        print(f"[{msg.action_id}] {status}: {action['name']}")
        
        # Stampa summary quando un'azione completa
        if msg.status in [2, 3]:  # SUCCEEDED o FAILED
            self.print_summary()
    
    def print_summary(self):
        """Stampa il riepilogo"""
        succeeded = sum(1 for a in self.actions.values() if '?' in str(a['status']))
        failed = sum(1 for a in self.actions.values() if '?' in str(a['status']))
        total = len(self.actions)
        
        print("\n" + "=" * 50)
        print(f"Progress: {succeeded}/{total} succeeded, {failed}/{total} failed")
        print("=" * 50)

if __name__ == '__main__':
    try:
        DispatchMonitor()
    except rospy.ROSInterruptException:
        pass
