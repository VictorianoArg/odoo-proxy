from flask import Flask, request, jsonify, send_from_directory
import requests

app = Flask(__name__, static_folder='.')

ODOO_URL = "https://sexfun.odoo.com"
session = requests.Session()

def cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    return response

@app.route("/", methods=["GET"])
def index():
    return send_from_directory('.', 'index.html')

@app.route("/proxy", methods=["POST", "OPTIONS"])
def proxy():
    if request.method == "OPTIONS":
        return cors(jsonify({}))

    body = request.get_json()
    path = body.get("path", "/web/dataset/call_kw")
    payload = body.get("payload", {})

    try:
        resp = session.post(
            f"{ODOO_URL}{path}",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=15
        )
        return cors(jsonify(resp.json()))
    except Exception as e:
        return cors(jsonify({"error": {"message": str(e)}})), 500

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
