from flask import Flask, render_template, request, redirect, jsonify
import random

app = Flask(__name__)

ledger_store = [
    {"id": 1, "name": "Rusted Exo-Leg", "cals": 1200, "sector": "SEC-09", "condition": 32, "sold": False},
    {"id": 2, "name": "Nuclear Cell (Empty)", "cals": 450, "sector": "SEC-12", "condition": 88, "sold": False}
]

@app.route('/')
def index():
    return render_template('index.html', ledger=ledger_store, online_users=random.randint(14, 89))

@app.route('/map')
def tactical_map():
    print("--- ACCESSING TACTICAL MAP ROUTE ---") # Check your terminal for this!
    return render_template('map.html', ledger=ledger_store)

@app.route('/scan')
def scan_for_scrap():
    if random.random() > 0.5:
        ghost_items = ["Bent I-Beam", "Filtered Water", "Tech-Shard", "Lead Pipe"]
        new_item = {
            "id": len(ledger_store) + 1,
            "name": random.choice(ghost_items),
            "cals": random.randint(50, 5000),
            "sector": f"SEC-{random.randint(1, 99)}",
            "condition": random.randint(5, 40),
            "sold": False
        }
        ledger_store.append(new_item)
        return jsonify({"status": "found", "item": new_item})
    return jsonify({"status": "searching"})

@app.route('/list', methods=['POST'])
def list_item():
    new_item = {
        "id": len(ledger_store) + 1,
        "name": request.form.get('item'),
        "cals": request.form.get('cals'),
        "sector": request.form.get('sector'),
        "condition": random.randint(10, 99),
        "sold": False
    }
    ledger_store.append(new_item)
    return redirect('/')

@app.route('/buy/<int:item_id>', methods=['POST'])
def buy_item(item_id):
    for item in ledger_store:
        if item['id'] == item_id:
            item['sold'] = True
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
