#!/usr/bin/env python3
"""
QTRobot Emotion Analysis Node
Riceve dati di emozione dal browser (MorphCast) via Flask
e li pubblica sul topic ROS /emotion/analysis
"""

import os
import yaml
import rospkg
import rospy
import threading
import time
import json
import logging
from typing import Optional

from std_msgs.msg import String, Float32
from flask import Flask, request, jsonify, Response, render_template

# ─── Configurazione e Lettura YAML ─────────────────────────────────────────────
FLASK_PORT  = 8000
PRINT_EVERY = 0.0

# Trova il file YAML automaticamente
try:
    rospack = rospkg.RosPack()
    pkg_path = rospack.get_path('thesis_qt')
    yaml_path = os.path.join(pkg_path, 'config', 'offline_conversation.yaml')
    
    with open(yaml_path, 'r') as file:
        config = yaml.safe_load(file)
        # Legge la chiave (se non c'è, restituisce stringa vuota)
        MORPHCAST_KEY = config.get('morphcast', {}).get('license_key', '')
        if not MORPHCAST_KEY:
            print("\n[ATTENZIONE] Chiave MorphCast non trovata nel file YAML!\n")
except Exception as e:
    print(f"\n[ERRORE] Impossibile leggere il file YAML: {e}\n")
    MORPHCAST_KEY = ""
# ───────────────────────────────────────────────────────────────────────────────

logging.getLogger("werkzeug").setLevel(logging.ERROR)

# Diciamo a Flask di cercare index.html in questa stessa cartella (scripts)
current_dir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, template_folder=current_dir)

_lock = threading.Lock()
_latest = {
    "dominant":   None,
    "confidence": None,
    "scores":     {},
    "arousal":    None,
    "valence":    None,
    "attention":  None,
}
_last_print_time = 0.0
emotion_pub: Optional[object] = None
attention_pub: Optional[object] = None

# Labels
EMOTION_LABELS = {
    "HAPPY": "H",
    "FEAR":      "F",
    "ANGRY":     "A",
    "SAD":   "SA",
    "SURPRISE":  "SU",
    "DISGUST":   "D",
    "NEUTRAL":   "N",
    "BORED":    "B" # non riconoscibile da morphcast, ma aggiunto per completezza
}


def _extract(data: dict):
    output = data.get("output", {})
    with _lock:
        for key in ("arousal", "valence", "attention"):
            val = output.get(key)
            if isinstance(val, dict):
                val = val.get("value")
            if val is not None:
                _latest[key] = round(float(val), 4)

        emotions_data = output.get("emotion")
        if emotions_data:
            if isinstance(emotions_data, dict) and "value" not in emotions_data:
                scores = emotions_data
            elif isinstance(emotions_data, dict) and "value" in emotions_data:
                scores = emotions_data.get("value", {})
            else:
                scores = {}

            if scores:
                dominant = max(scores, key=scores.get)
                _latest["dominant"]   = dominant
                _latest["confidence"] = round(scores[dominant], 4)
                _latest["scores"]     = {k: round(v, 4) for k, v in scores.items()}


@app.route("/")
def index():
    # render_template inietta la variabile "key" dentro l'HTML
    return render_template("index.html", key=MORPHCAST_KEY)


@app.route("/frame")
def frame():
    import urllib.request
    try:
        url = "http://127.0.0.1:8080/snapshot?topic=/camera/color/image_raw&width=320&height=240"
        req = urllib.request.urlopen(url, timeout=2)
        data = req.read()
        return Response(data, content_type="image/jpeg")
    except Exception as e:
        print(f"[frame] ERRORE: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/video_proxy")
def video_proxy():
    import urllib.request
    url = "http://127.0.0.1:8080/stream?topic=/camera/color/image_raw&type=mjpeg&width=320&height=240&framerate=15"
    try:
        req = urllib.request.urlopen(url, timeout=5)
        def generate():
            try:
                while True:
                    chunk = req.read(4096)
                    if not chunk:
                        break
                    yield chunk
            except Exception as e:
                print(f"[proxy] stream interrotto: {e}")
        return Response(generate(), content_type=req.headers.get("Content-Type", "multipart/x-mixed-replace"))
    except Exception as e:
        print(f"[proxy] ERRORE: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/process_data", methods=["POST"])
def process_data():
    global _last_print_time

    data = request.get_json(force=True, silent=True) or {}
    _extract(data)

    now = time.time()
    if now - _last_print_time >= PRINT_EVERY:
        with _lock:
            if _latest["dominant"]:
                print("\n--- EMOZIONE CORRENTE ---")
                print(f"Dominante:  {_latest['dominant'].upper()} (Confidenza: {_latest['confidence']})")
                print(f"Valence:    {_latest['valence']}")
                print(f"Arousal:    {_latest['arousal']}")
                print(f"Attention:  {_latest['attention']}")
                print("-------------------------")
        _last_print_time = now

    if emotion_pub is not None:
        with _lock:
            dominant = _latest.get("dominant")
            label = EMOTION_LABELS.get(dominant.upper(), "N") if dominant else "N"
            msg = String()
            msg.data = label
        emotion_pub.publish(msg)

    if attention_pub is not None:
        with _lock:
            attention_val = _latest.get("attention")
        if attention_val is not None:
            attention_pub.publish(Float32(data=attention_val))

    return jsonify({"success": True}), 200


@app.route("/current_emotion", methods=["GET"])
def current_emotion():
    with _lock:
        return jsonify(_latest), 200


if __name__ == "__main__":
    rospy.init_node("emotion_analysis_node", anonymous=False)
    rospy.loginfo("[emotion_node] Starting up...")
    
    # Stampa i primi 5 caratteri della chiave per sicurezza per verificare che l'abbia letta
    partial_key = f"{MORPHCAST_KEY[:5]}..." if len(MORPHCAST_KEY) > 5 else "VUOTA"
    rospy.loginfo(f"[emotion_node] Chiave Morphcast caricata: {partial_key}")

    emotion_pub = rospy.Publisher("/emotion/analysis", String, queue_size=10)
    attention_pub = rospy.Publisher("/attention/analysis", Float32, queue_size=10)

    flask_thread = threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=FLASK_PORT, debug=False),
        daemon=True,
        name="flask-server"
    )
    flask_thread.start()
    rospy.loginfo(f"[emotion_node] Web server on http://0.0.0.0:{FLASK_PORT}")
    rospy.loginfo("[emotion_node] Apri http://127.0.0.1:8000 dal browser del tuo PC")

    rospy.spin()