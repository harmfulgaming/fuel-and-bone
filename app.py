from flask import Flask, render_template, request, jsonify, redirect
import random, threading, time, json, os

app = Flask(__name__)

# =========================
# CONFIG
# =========================

DATA_FILE = "save_data.json"
STARTING_CREDITS = 100
MAX_WORLD_ITEMS = 25

lock = threading.Lock()

user_wallet = STARTING_CREDITS
ledger_store = []
player_inventory = {"materials": {}}
player_cooldowns = {}

# =========================
# MARKET SYSTEM (ANTI-CHEAT)
# =========================

MARKET_HISTORY = {}
MARKET_PRICE = {}

def update_market(item):
    name = item["name"]
    price = item["cals"]

    MARKET_HISTORY.setdefault(name, []).append(price)

    if len(MARKET_HISTORY[name]) > 20:
        MARKET_HISTORY[name].pop(0)

    MARKET_PRICE[name] = sum(MARKET_HISTORY[name]) / len(MARKET_HISTORY[name])

def market_cap(item):
    base = MARKET_PRICE.get(item["name"], item["cals"])
    return base * 1.2

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

HARVEST_ZONES = [
    {"id": 1, "name": "North Ridge", "lat": 40.7, "lng": -74.0},
    {"id": 2, "name": "Desert Grid", "lat": 35.0, "lng": -115.0},
    {"id": 3, "name": "Frozen Core", "lat": 64.1, "lng": -21.9}
]

RECIPES = {
    "Basic Core": {"Scrap": 100, "Circuit": 50},
    "Energy Core": {"Energy": 60, "Circuit": 80},
    "Void Relic": {"Scrap": 200, "Circuit": 150, "Energy": 100}
}

# =========================
# WORLD LIMIT
# =========================

def can_spawn():
    return len(ledger_store) < MAX_WORLD_ITEMS

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
# ITEM SYSTEM
# =========================

def roll_rarity():
    r = random.randint(1, 100)
    if r == 1:
        return "legendary"
    if r <= 8:
        return "epic"
    if r <= 30:
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

        # 🌍 REAL COORDS FOR SCAV-NET MAP
        "lat": random.uniform(-80, 80),
        "lng": random.uniform(-180, 180),

        "current_bid": 0,
        "highest_bidder": None,
        "end_time": time.time() + random.randint(10, 25)
    }

# =========================
# INIT WORLD
# =========================

load_data()

if not ledger_store:
    ledger_store = [gen_item() for _ in range(8)]

# =========================
# SCAN SYSTEM (SCAV-NET)
# =========================

@app.route("/scan")
def scan():
    with lock:
        if not ledger_store:
            return jsonify({"status": "nothing"})

        if random.random() < 0.4:
            item = random.choice(ledger_store)

            x = (item["lng"] + 180) / 360 * 100
            y = (90 - item["lat"]) / 180 * 100

            return jsonify({
                "status": "found",
                "item": {
                    "name": item["name"],
                    "rarity": item["rarity"],
                    "x": x,
                    "y": y
                }
            })

    return jsonify({"status": "nothing"})

# =========================
# HARVEST SYSTEM
# =========================

@app.route("/harvest/<int:zone_id>", methods=["POST"])
def harvest(zone_id):
    now = time.time()

    with lock:
        if player_cooldowns.get(zone_id, 0) > now:
            return jsonify({"status": "cooldown"})

        loot = {
            "Scrap": random.randint(20, 100),
            "Circuit": random.randint(10, 50),
            "Energy": random.randint(5, 30)
        }

        for k, v in loot.items():
            player_inventory["materials"][k] = player_inventory["materials"].get(k, 0) + v

        player_cooldowns[zone_id] = now + 20

    return jsonify({"status": "ok", "loot": loot})

# =========================
# CRAFTING
# =========================

@app.route("/craft/<item>", methods=["POST"])
def craft(item):
    with lock:
        if item not in RECIPES:
            return jsonify({"status": "invalid"})

        inv = player_inventory["materials"]

        for k, v in RECIPES[item].items():
            if inv.get(k, 0) < v:
                return jsonify({"status": "not enough"})

        for k, v in RECIPES[item].items():
            inv[k] -= v

        if can_spawn():
            ledger_store.append(gen_item("crafted"))

    return jsonify({"status": "crafted"})

# =========================
# BOT LOGIC (SMART + MARKET SAFE)
# =========================

def bot_bid(bot, item):
    cap = market_cap(item)

    if item["current_bid"] > cap:
        return

    if item["cals"] > bot["wallet"]:
        return

    score = item["cals"] * (item["condition"] / 100)

    if bot["type"] == "sniper":
        score *= 1.4 if item["rarity"] == "legendary" else 0.7

    if bot["type"] == "value_hunter":
        score *= 1.2 if item["cals"] < cap else 0.6

    if score <= item["current_bid"]:
        return

    bid = item["current_bid"] + random.randint(10, 80)
    bid = min(bid, cap)

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
            items = list(ledger_store)

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

                    update_market(item)

                    ledger_store = [i for i in ledger_store if i["id"] != item["id"]]

                    if can_spawn():
                        ledger_store.append(gen_item())

                    save_data()

# =========================
# BOARD SHUFFLER
# =========================

def board_shuffler():
    while True:
        time.sleep(40)

        with lock:
            if ledger_store and can_spawn():
                ledger_store.pop(random.randint(0, len(ledger_store)-1))
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

@app.route("/list", methods=["POST"])
def list_item():
    with lock:
        if can_spawn():
            item = gen_item("user")
            item["name"] = request.form.get("item")
            item["cals"] = int(request.form.get("cals"))

            ledger_store.append(item)
            save_data()

    return redirect("/")

# =========================
# START
# =========================

if __name__ == "__main__":

    # =========================
    # WORLD LOOP (GAME ENGINE)
    # =========================
    def world_events():
        global user_wallet

        while True:
            time.sleep(5)

            with lock:
                # 🌍 passive income
                user_wallet += random.randint(1, 5)

                # 🔥 world spawning system
                if len(ledger_store) < MAX_WORLD_ITEMS and random.random() < 0.2:
                    ledger_store.append(gen_item("world_event"))

                # 🤖 bot idle behavior
                for bot in BOTS:
                    if random.random() < 0.1:
                        bot["wallet"] += random.randint(1, 10)

                save_data()

    # =========================
    # START BACKGROUND THREADS
    # =========================
    threads = [
        threading.Thread(target=auction_engine, daemon=True),
        threading.Thread(target=board_shuffler, daemon=True),
        threading.Thread(target=world_events, daemon=True),
    ]

    for t in threads:
        t.start()

    # =========================
    # START FLASK SERVER
    # =========================
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
        use_reloader=False  # IMPORTANT for Docker stability
    )
