"""Notification microservice (stub opcional): umbrales riego / carencia.

Escucha MQTT y registra alertas en memoria (email/MQTT out pendiente).
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any

import paho.mqtt.client as mqtt
from fastapi import FastAPI

MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
IRRIGATION_FLOW_MIN = float(os.getenv("ALERT_IRRIGATION_FLOW_MIN", "0.1"))
REEFER_TEMP_MAX = float(os.getenv("ALERT_REEFER_TEMP_MAX", "8.0"))

app = FastAPI(title="AgroPS Notification Service", version="0.1.0")
_alerts: list[dict[str, Any]] = []


def _emit(kind: str, topic: str, payload: dict[str, Any], message: str) -> None:
    alert = {
        "kind": kind,
        "topic": topic,
        "message": message,
        "payload": payload,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    _alerts.insert(0, alert)
    del _alerts[200:]
    print(f"[notification] {kind}: {message}", flush=True)


def _on_message(_c, _u, msg: mqtt.MQTTMessage) -> None:
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
    except Exception:
        return
    topic = msg.topic
    if topic.startswith("finca/") and topic.endswith("/riego"):
        val = payload.get("caudal", payload.get("value"))
        if val is not None and float(val) < IRRIGATION_FLOW_MIN:
            _emit("irrigation_low", topic, payload, f"Caudal bajo: {val}")
    if topic.startswith("reefer/") and topic.endswith("/temp"):
        val = payload.get("temp", payload.get("temperature", payload.get("value")))
        if val is not None and float(val) > REEFER_TEMP_MAX:
            _emit("reefer_hot", topic, payload, f"Temp reefer alta: {val}")


def _start_mqtt() -> None:
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    except AttributeError:
        client = mqtt.Client()
    client.on_message = _on_message

    def on_connect(c, *_a):
        c.subscribe("finca/+/riego")
        c.subscribe("reefer/+/temp")
        print("[notification] MQTT subscribed", flush=True)

    client.on_connect = on_connect
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.loop_start()


@app.on_event("startup")
def startup() -> None:
    threading.Thread(target=_start_mqtt, daemon=True).start()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "notification"}


@app.get("/v1/alerts")
def alerts(limit: int = 50) -> dict[str, Any]:
    return {"items": _alerts[:limit]}
