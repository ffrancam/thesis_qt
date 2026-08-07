#!/usr/bin/env python3
import sys
import subprocess
import re

domain = sys.argv[1]
problem = sys.argv[2]

cmd = [
    "java", "-jar",
    "/root/ros_ws/src/thesis_qt/planners/ENHSP-Public/enhsp-dist/enhsp.jar",
    "-o", domain,
    "-f", problem
]

result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
output = result.stdout

plan_started = False

for line in output.splitlines():
    line = line.strip()   # ?? FIX CRUCIALE

    if "Found Plan:" in line:
        plan_started = True
        continue

    if plan_started:
        if line == "":
            continue

        if "Plan-Length" in line:
            break

        # ?? usa search invece di match
        match = re.search(r"([0-9.]+):\s*(\(.*\))", line)
        if match:
            time = match.group(1)
            action = match.group(2)
            print(f"{time}: {action} [1.000]")
