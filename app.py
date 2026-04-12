import json
import os
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)
DB_FILE = 'fuel_and_bone_ledger.json'

def get_ledger():
    if not os.path.exists(DB_FILE):
        return []
    with open(DB_FILE, 'r') as f:
        return json.load(f)

def commit_to_ledger(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f)

@app.route('/')
def index():
    ledger = get_ledger()
    return render_template('index.html', ledger=ledger)

@app.route('/list', methods=['POST'])
def list_item():
    ledger = get_ledger()
   new_item = {
    'id': len(ledger) + 1,
    'name': request.form.get('item'),
    'price': request.form.get('price'), # Changed from cals
    'sector': request.form.get('sector'),
    'condition': request.form.get('condition'),
    'sold': False
}
    }
    ledger.append(new_item)
    commit_to_ledger(ledger)
    return redirect(url_for('index'))

@app.route('/buy/<int:item_id>', methods=['POST'])
def buy_item(item_id):
    ledger = get_ledger()
    for item in ledger:
        if item['id'] == item_id:
            item['sold'] = True
    commit_to_ledger(ledger)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
@app.route('/scrap/<int:item_id>', methods=['POST'])
def scrap_item(item_id):
    ledger = get_ledger()
    ledger = [item for item in ledger if item['id'] != item_id]
    commit_to_ledger(ledger)
    return redirect(url_for('index'))
