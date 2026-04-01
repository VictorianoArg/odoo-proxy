from flask import Flask, request, jsonify, send_from_directory
import xmlrpc.client
import requests

app = Flask(__name__, static_folder='.')

ODOO_URL = "https://sexfun.odoo.com"
ODOO_DB = "sexfun"
ODOO_USER = "gerencia@sexfun.com.ar"
ODOO_APIKEY = "34816db4a33311bf1ddb5d627ed8ca944d8edcba"
ANTHROPIC_KEY = "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"

uid = None

def get_uid():
    global uid
    if uid:
        return uid
    common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
    uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_APIKEY, {})
    if not uid:
        raise Exception("Autenticación fallida en Odoo")
    return uid

def odoo_rpc(model, method, args, kwargs):
    user_id = get_uid()
    models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")
    return models.execute_kw(ODOO_DB, user_id, ODOO_APIKEY, model, method, args, kwargs)

def cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    return response

@app.route("/", methods=["GET"])
def index():
    return send_from_directory('.', 'index.html')

@app.route("/ask", methods=["POST", "OPTIONS"])
def ask():
    if request.method == "OPTIONS":
        return cors(jsonify({}))

    body = request.get_json()
    query = body.get("query", "")
    q = query.lower()
    data = {}

    try:
        if any(w in q for w in ['provincia','factur','cliente','venta','top','mes']):
            invoices = odoo_rpc('account.move', 'search_read',
                [[['move_type','in',['out_invoice','out_refund']], ['state','=','posted']]],
                {'fields': ['name','partner_id','amount_total','invoice_date','payment_state'], 'limit': 300, 'order': 'invoice_date desc'}
            )
            data['facturas'] = invoices
            ids = list(set([i['partner_id'][0] for i in invoices if i.get('partner_id')]))
            if ids:
                data['clientes'] = odoo_rpc('res.partner', 'search_read',
                    [[['id','in',ids]]],
                    {'fields': ['id','name','state_id','country_id','city','vat']}
                )

        if any(w in q for w in ['stock','producto','inventario','bajo']):
            data['productos'] = odoo_rpc('product.product', 'search_read',
                [[['type','=','product']]],
                {'fields': ['name','qty_available','virtual_available','list_price'], 'limit': 150}
            )

        if any(w in q for w in ['pagar','deuda','pendiente','cobrar']):
            data['pendientes'] = odoo_rpc('account.move', 'search_read',
                [[['move_type','=','out_invoice'],['payment_state','in',['not_paid','partial']],['state','=','posted']]],
                {'fields': ['name','partner_id','amount_total','amount_residual','invoice_date_due'], 'limit': 100}
            )

        if any(w in q for w in ['compra','proveedor']):
            data['compras'] = odoo_rpc('purchase.order', 'search_read',
                [[['state','in',['purchase','done']]]],
                {'fields': ['name','partner_id','amount_total','date_order'], 'limit': 100}
            )

    except Exception as e:
        global uid
        uid = None
        return cors(jsonify({"error": f"Error al consultar Odoo: {str(e)}"})), 500

    try:
        import json
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "Content-Type": "application/json",
                "x-api-key": ANTHROPIC_KEY,
                "anthropic-version": "2023-06-01"
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1000,
                "system": "Sos un asistente de análisis de datos para SexFun, empresa argentina. Respondé en español, claro y conciso. Analizá solo los datos recibidos, nunca inventes. Si hay provincias argentinas, usá sus nombres completos. Presentá números y rankings ordenados.",
                "messages": [{"role": "user", "content": f'Consulta: "{query}"\n\nDatos de Odoo:\n{json.dumps(data, ensure_ascii=False)}\n\nRespondé basándote únicamente en estos datos.'}]
            },
            timeout=30
        )
        result = resp.json()
        answer = result["content"][0]["text"]
        return cors(jsonify({"answer": answer}))
    except Exception as e:
        return cors(jsonify({"error": f"Error al consultar IA: {str(e)}"})), 500

@app.route("/health", methods=["GET"])
def health():
    try:
        get_uid()
        return jsonify({"status": "ok", "uid": uid})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
