from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

ODOO_URL = "https://sexfun.odoo.com"

@app.route("/proxy", methods=["POST", "OPTIONS"])
def proxy():
    if request.method == "OPTIONS":
        response = jsonify({})
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        return response

    path = request.json.get("path", "/web/dataset/call_kw")
    payload = request.json.get("payload", {})

    resp = requests.post(
        f"{ODOO_URL}{path}",
        json=payload,
        headers={"Content-Type": "application/json"},
        cookies=request.cookies
    )

    response = jsonify(resp.json())
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.set_cookie("session_id", resp.cookies.get("session_id", ""))
    return response

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
