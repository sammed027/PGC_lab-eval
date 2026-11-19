"""Flask application used to demonstrate Kubernetes health probes.

The flags are deliberately process-local so that a container restart resets
the application to its initial healthy state. This is a lab demonstration,
not a production health-state implementation.
"""
from flask import Flask, jsonify

app = Flask(__name__)

liveness_ok = True
readiness_ok = True


@app.get("/")
def home():
    return jsonify(
        application="Kubernetes Health Check Demo",
        status="Running",
        endpoints=["/live", "/ready", "/fail-liveness",
                   "/fail-readiness", "/recover"],
    ), 200


@app.get("/live")
def liveness():
    if not liveness_ok:
        return jsonify(status="Dead", check="liveness"), 500
    return jsonify(status="Alive", check="liveness"), 200


@app.get("/ready")
def readiness():
    if not readiness_ok:
        return jsonify(status="Not Ready", check="readiness"), 503
    return jsonify(status="Ready", check="readiness"), 200


@app.post("/fail-liveness")
def fail_liveness():
    global liveness_ok
    liveness_ok = False
    return jsonify(message="Liveness failure enabled"), 200


@app.post("/fail-readiness")
def fail_readiness():
    global readiness_ok
    readiness_ok = False
    return jsonify(message="Readiness failure enabled"), 200


@app.post("/recover")
def recover():
    global liveness_ok, readiness_ok
    liveness_ok = True
    readiness_ok = True
    return jsonify(message="Application health states restored"), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
