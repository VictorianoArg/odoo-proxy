from flask import Flask, request, jsonify, send_from_directory
import requests
import xmlrpc.client

app = Flask(__name__, static_folder='.')

ODOO_URL = "https://sexfun.odoo.com"
ODOO_DB = "sexfun"
ODOO_USER = "gerencia@sexfun.com.ar"
ODOO_APIKEY = "34816db4a33311bf1ddb5d627ed8ca944d8edcba"

uid = None

def get_uid():
    global uid
    if uid:
        return uid
    common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
    uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_APIKEY, {})
    if not uid:
        raise Exception("Autenticación fallida")
    return uid

def cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    return response

@app.route("/", methods=["GET"])
def index():
    return send_from_directory('.', 'index.html')

@app.route("/rpc", methods=["POST", "OPTIONS"])
def rpc():
    if request.method == "OPTIONS":
        return cors(jsonify({}))

    body = request.get_json()
    model = body.get("model")
    method = body.get("method")
    args = body.get("args", [])
    kwargs = body.get("kwargs", {})

    try:
        user_id = get_uid()
        models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")
        result = models.execute_kw(ODOO_DB, user_id, ODOO_APIKEY, model, method, args, kwargs)
        return cors(jsonify({"result": result}))
    except Exception as e:
        global uid
        uid = None
        return cors(jsonify({"error": str(e)})), 500

@app.route("/health", methods=["GET"])
def health():
    try:
        get_uid()
        return jsonify({"status": "ok", "uid": uid})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
