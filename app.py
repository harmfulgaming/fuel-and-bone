from flask import Flask, render_template, request, jsonify, redirect
import random, threading, time, json, os

app = Flask(__name__)

# =========================
# CONFIG
# =========================

DATA_FILE = "save_data.json"
OFFLINE_MODE = False
STARTING_CREDITS = 100

lock = threading.Lock()

user_wallet = STARTING_CREDITS
ledger_store = []
player_inventory = {"materials": {}}
player_cooldowns = {}

# =========================
# BOT SYSTEM
# =========================

BOTS = [
    {"id": 1, "type": "sniper", "wallet": STARTING_CREDITS},
    {"id": 2, "type": "value_hunter", "wallet": STARTING_CREDITS},
    {"id": 3, "type": "whale", "wallet": STARTING_CREDITS},
]

# =========================
# WORLD DATA
# =========================

G_NAMES = ["Rusted Exo-Leg", "Nuclear Cell", "Void-Plate", "Ion Battery", "Tech-Shard"]

G_SECTORS = ["SEC-09", "SEC-12", "SEC-44"]

HARVEST_ZONES = [
    {"id": 1, "name": "North Ridge", "lat": 40.7, "lng": -74.0},
    {"id": 2, "name": "Desert Grid", "lat": 35.0, "lng": -115.0},
    {"id": 3, "name": "Frozen Core", "lat": 64.1, "lng": -21.9}
]

RARITIES = {
    "common": 70,
    "rare": 22,
    "epic": 7,
    "legendary": 1
}

RECIPES = {
    "Basic Core": {"Scrap": 100, "Circuit": 50},
    "Energy Core": {"Energy": 60, "Circuit": 80},
    "Void Relic": {"Scrap": 200, "Circuit": 150, "Energy": 100}
}

# =========================
# SAVE / LOAD
# =========================

def save_data():
    with lock:
        with open(DATA_FILE, "w") as f:
            json.dump({
                "wallet": user_wallet,
                "ledger": ledger_store,
                "bots": BOTS,
                "inventory": player_inventory
            }, f)


def load_data():
    global user_wallet, ledger_store, player_inventory

    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                user_wallet = data.get("wallet", STARTING_CREDITS)
                ledger_store = data.get("ledger", [])
                player_inventory = data.get("inventory", {"materials": {}})
        except:
            pass


# =========================
# RARITY + ITEMS
# =========================

def roll_rarity():
    r = random.randint(1, 100)
    if r == 1:
        return "legendary"
    elif r <= 8:
        return "epic"
    elif r <= 30:
        return "rare"
    return "common"


def gen_item(origin="system"):
    rarity = roll_rarity()
    mult = {"common":1, "rare":1.5, "epic":2.5, "legendary":5}[rarity]

    return {
        "id": random.randint(1000, 9999),
        "name": random.choice(G_NAMES),
        "rarity": rarity,
        "cals": int(random.randint(100, 1500) * mult),
        "condition": random.randint(10, 100),
        "origin": origin,
        "current_bid": 0,
        "highest_bidder": None,
        "end_time": time.time() + random.randint(10, 25)
    }


# init world
load_data()
if not ledger_store:
    ledger_store = [gen_item() for _ in range(8)]


# =========================
# BOT LOGIC
# =========================

def evaluate(bot, item):
    rarity_bonus = {"common":1, "rare":1.3, "epic":1.8, "legendary":3}[item["rarity"]]
    score = item["cals"] * (item["condition"]/100) * rarity_bonus

    if bot["type"] == "sniper":
        score *= 1.4 if item["rarity"] in ["epic","legendary"] else 0.7
    elif bot["type"] == "value_hunter":
        score *= 1.2 if item["rarity"] == "rare" else 0.9

    return score


def bot_bid(bot, item):
    if item["cals"] > bot["wallet"]:
        return

    if evaluate(bot, item) < item["current_bid"]:
        return

    bid = item["current_bid"] + random.randint(10, 120)

    if bid <= bot["wallet"]:
        item["current_bid"] = bid
        item["highest_bidder"] = bot["id"]


# =========================
# AUCTION ENGINE
# =========================

def auction_engine():
    global user_wallet, ledger_store

    while True:
        time.sleep(2)

        with lock:
            items = [i for i in ledger_store if i["origin"] in ["user","system"]]

        for item in items:

            with lock:
                for bot in BOTS:
                    if random.random() < 0.5:
                        bot_bid(bot, item)

            if time.time() > item["end_time"]:

                with lock:

                    if item["highest_bidder"]:
                        winner = next((b for b in BOTS if b["id"] == item["highest_bidder"]), None)

                        if winner:
                            price = item["current_bid"]
                            winner["wallet"] -= price
                            user_wallet += price
                            print(f"SOLD {item['name']} -> {winner['type']} for {price}")

                    ledger_store = [i for i in ledger_store if i["id"] != item["id"]]

                    new_item = gen_item()
                    if new_item:
                        ledger_store.append(new_item)

                    save_data()


# =========================
# MAP HARVEST SYSTEM
# =========================

def harvest(zone_id):
    now = time.time()

    if player_cooldowns.get(zone_id,0) > now:
        return {"status":"cooldown"}

    loot = {
        "Scrap": random.randint(20,100),
        "Circuit": random.randint(10,50),
        "Energy": random.randint(5,30)
    }

    for k,v in loot.items():
        player_inventory["materials"][k] = player_inventory["materials"].get(k,0) + v

    player_cooldowns[zone_id] = now + 20

    return {"status":"ok","loot":loot}


# =========================
# CRAFTING
# =========================

def craft(item):
    if item not in RECIPES:
        return {"status":"invalid"}

    inv = player_inventory["materials"]

    for k,v in RECIPES[item].items():
        if inv.get(k,0) < v:
            return {"status":"not enough"}

    for k,v in RECIPES[item].items():
        inv[k] -= v

    ledger_store.append(gen_item("crafted"))

    return {"status":"crafted"}


# =========================
# THREADS
# =========================

def board_shuffler():
    while True:
        time.sleep(40)
        with lock:
            if ledger_store:
                ledger_store.pop(random.randint(0,len(ledger_store)-1))
                ledger_store.append(gen_item())
                save_data()


# =========================
# ROUTES
# =========================

@app.route("/")
def home():
    return render_template("index.html", ledger=ledger_store, wallet=user_wallet)

@app.route("/map")
def map_page():
    return render_template("map.html", zones=HARVEST_ZONES)

@app.route("/harvest/<int:zone_id>", methods=["POST"])
def harvest_route(zone_id):
    return jsonify(harvest(zone_id))

@app.route("/craft/<name>", methods=["POST"])
def craft_route(name):
    return jsonify(craft(name))

@app.route("/list", methods=["POST"])
def list_item():
    with lock:
        ledger_store.append({
            **gen_item("user"),
            "name": request.form.get("item"),
            "cals": int(request.form.get("cals"))
        })
        save_data()

    return redirect("/")


# =========================
# START
# =========================

if __name__ == "__main__":
    if not OFFLINE_MODE:
        threading.Thread(target=auction_engine, daemon=True).start()
        threading.Thread(target=board_shuffler, daemon=True).start()

    app.run(debug=False, host="0.0.0.0", port=5000)
