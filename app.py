from flask import Flask, render_template, request, redirect
import json, requests

app = Flask(__name__)
DATA_FILE = "portfolio.json"

# -----------------------------
# Load / Save Portfolio
# -----------------------------
def load_portfolio():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_portfolio(portfolio):
    with open(DATA_FILE, "w") as f:
        json.dump(portfolio, f, indent=4)

# -----------------------------
# Coin Validation (Cached)
# -----------------------------
coin_cache = None

def get_coin_list():
    global coin_cache
    if coin_cache is None:
        try:
            url = "https://api.coingecko.com/api/v3/coins/list"
            response = requests.get(url, timeout=10)
            coin_cache = [c["id"] for c in response.json()]
        except:
            coin_cache = []
    return coin_cache

def is_valid_coin(coin):
    return coin in get_coin_list()

# -----------------------------
# Fetch Prices (Bulk)
# -----------------------------
def fetch_prices(coins):
    try:
        if not coins:
            return {}
        ids = ",".join(coins)
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd"
        response = requests.get(url, timeout=10)
        return response.json()
    except:
        return {}

# -----------------------------
# Main Route
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    portfolio = load_portfolio()
    error_message = None

    # -------------------------
    # ADD COIN
    # -------------------------
    if request.method == "POST" and "add" in request.form:
        coin = request.form["coin"].lower().strip()

        try:
            qty = float(request.form["quantity"])
            buy_price = float(request.form["buy_price"])
        except ValueError:
            error_message = "❌ Invalid number input"
            return render_template("index.html", portfolio=portfolio, error_message=error_message)

        if not is_valid_coin(coin):
            error_message = f"❌ '{coin}' is not a valid cryptocurrency"
        else:
            existing = next((c for c in portfolio if c["coin"] == coin), None)

            if existing:
                existing["quantity"] += qty
                existing["buy_price"] = buy_price
            else:
                portfolio.append({
                    "coin": coin,
                    "quantity": qty,
                    "buy_price": buy_price
                })

            save_portfolio(portfolio)
            return redirect("/")

    # -------------------------
    # EDIT COIN
    # -------------------------
    if request.method == "POST" and "edit" in request.form:
        coin = request.form["coin"].lower().strip()

        try:
            qty = float(request.form["quantity"])
            buy_price = float(request.form["buy_price"])
        except ValueError:
            return redirect("/")

        for c in portfolio:
            if c["coin"] == coin:
                c["quantity"] = qty
                c["buy_price"] = buy_price
                break

        save_portfolio(portfolio)
        return redirect("/")

    # -------------------------
    # DELETE COIN
    # -------------------------
    if request.method == "POST" and "delete" in request.form:
        coin = request.form["coin"].lower().strip()
        portfolio = [c for c in portfolio if c["coin"] != coin]
        save_portfolio(portfolio)
        return redirect("/")

    # -------------------------
    # CALCULATIONS
    # -------------------------
    total_investment, total_value = 0, 0
    best_coin, worst_coin = None, None
    best_pl = float("-inf")
    worst_pl = float("inf")

    coins = [c["coin"] for c in portfolio]
    price_data = fetch_prices(coins)

    for c in portfolio:
        investment = c["quantity"] * c["buy_price"]

        current_price = price_data.get(c["coin"], {}).get("usd")
        if current_price is None:
            current_price = c["buy_price"]

        current_value = c["quantity"] * current_price
        profit_loss = current_value - investment

        c["current_price"] = current_price
        c["value"] = current_value
        c["profit_loss"] = profit_loss

        total_investment += investment
        total_value += current_value

        if profit_loss > best_pl:
            best_pl = profit_loss
            best_coin = c["coin"]

        if profit_loss < worst_pl:
            worst_pl = profit_loss
            worst_coin = c["coin"]

    net_profit_loss = total_value - total_investment

    if not portfolio:
        best_coin, worst_coin = "N/A", "N/A"
        best_pl, worst_pl = 0, 0

    return render_template(
        "index.html",
        portfolio=portfolio,
        total_investment=total_investment,
        total_value=total_value,
        net_profit_loss=net_profit_loss,
        best_coin=best_coin,
        best_pl=best_pl,
        worst_coin=worst_coin,
        worst_pl=worst_pl,
        error_message=error_message
    )

# -----------------------------
# RUN APP
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)