#!/usr/bin/env python3
"""
Jita profitability checker for:
  - Deflection Shield Emitter

Final item:
  - Uses highest Jita BUY order (what you can sell it for instantly)

Materials:
  - Uses lowest Jita SELL orders (what you pay to buy them)
  - Total material cost is multiplied by:
        MATERIAL_COST_MULTIPLIER * OVERHEAD_COST_MULTIPLIER
"""

import sys
import requests

# --- User-tunable settings --------------------------------------------------

# Multiply the raw material cost by this factor (e.g. 0.9 for 10% discount)
MATERIAL_COST_MULTIPLIER = 0.9

# Extra overhead multiplier (taxes, fees, hauling, etc.)
# e.g. 1.1 = +10% overhead on top of (discounted) material cost
OVERHEAD_COST_MULTIPLIER = 1.1

# --- Constants --------------------------------------------------------------

# Type IDs
TYPE_DEFLECTION_SHIELD_EMITTER = 11555     # Deflection Shield Emitter
TYPE_FERNITE_CARBIDE            = 16673    # Fernite Carbide
TYPE_SYLRAMIC_FIBERS            = 16678    # Sylramic Fibers
TYPE_FERROGEL                   = 16683    # Ferrogel

# Blueprint materials for 1 Deflection Shield Emitter at ME 10 (10/20 BPO)
MATERIALS = {
    "Fernite Carbide": {
        "type_id": TYPE_FERNITE_CARBIDE,
        "needed": 20,
    },
    "Sylramic Fibers": {
        "type_id": TYPE_SYLRAMIC_FIBERS,
        "needed": 9,
    },
    "Ferrogel": {
        "type_id": TYPE_FERROGEL,
        "needed": 1,
    },
}

REGION_ID = 10000002       # The Forge
JITA_SYSTEM_ID = 30000142  # Jita
ESI_URL = f"https://esi.evetech.net/latest/markets/{REGION_ID}/orders/"

HEADERS = {
    "User-Agent": "JitaDeflectionEmitterChecker/1.5 (youremail@example.com)"
}


# --- Helpers ---------------------------------------------------------------

def fetch_orders_for_type(type_id: int):
    """Fetch all market orders in the region for the given type_id."""
    all_orders = []

    params = {
        "datasource": "tranquility",
        "order_type": "all",
        "type_id": type_id,
        "page": 1,
    }

    while True:
        resp = requests.get(ESI_URL, headers=HEADERS, params=params, timeout=10)
        resp.raise_for_status()

        page_orders = resp.json()
        all_orders.extend(page_orders)

        x_pages = resp.headers.get("X-Pages")
        if not x_pages:
            break
        if params["page"] >= int(x_pages):
            break

        params["page"] += 1

    return all_orders


def get_best_order_in_system(type_id: int, system_id: int, *, buy: bool):
    """
    Return the best order in `system_id` for `type_id`.

    - If buy=True:   highest buy order
    - If buy=False:  lowest sell order
    """
    orders = fetch_orders_for_type(type_id)
    sys_orders = [o for o in orders if o.get("system_id") == system_id]

    if buy:
        sys_buy_orders = [o for o in sys_orders if o.get("is_buy_order") is True]
        if not sys_buy_orders:
            return None
        return max(sys_buy_orders, key=lambda o: o["price"])
    else:
        sys_sell_orders = [o for o in sys_orders if o.get("is_buy_order") is False]
        if not sys_sell_orders:
            return None
        return min(sys_sell_orders, key=lambda o: o["price"])


# --- Main logic ------------------------------------------------------------

def main():
    try:
        # Final product: highest BUY in Jita
        emitter_buy_order = get_best_order_in_system(
            TYPE_DEFLECTION_SHIELD_EMITTER, JITA_SYSTEM_ID, buy=True
        )

        # Materials: lowest SELL in Jita
        material_orders = {}
        for name, info in MATERIALS.items():
            order = get_best_order_in_system(info["type_id"], JITA_SYSTEM_ID, buy=False)
            material_orders[name] = order

    except requests.RequestException as e:
        print(f"Error talking to ESI: {e}", file=sys.stderr)
        sys.exit(1)

    # If we can't price the final item, bail out
    if emitter_buy_order is None:
        print("Deflection Shield Emitter: cannot compute profit (no Jita BUY orders).")
        sys.exit(0)

    # Compute total material cost from SELL orders
    total_material_cost = 0.0
    for name, info in MATERIALS.items():
        needed = info["needed"]
        order = material_orders[name]

        if order is None:
            print("Deflection Shield Emitter: cannot compute profit "
                  f"(no Jita SELL orders for {name}).")
            sys.exit(0)

        sell_price = order["price"]
        total_material_cost += sell_price * needed

    # Apply user-tunable multipliers
    discounted_cost = total_material_cost * MATERIAL_COST_MULTIPLIER
    adjusted_cost = discounted_cost * OVERHEAD_COST_MULTIPLIER

    # Final item price (instant sell to highest BUY)
    final_price = emitter_buy_order["price"]
    buy_volume = emitter_buy_order["volume_remain"]  # number of units being bought

    profit_isk = final_price - adjusted_cost
    if adjusted_cost > 0:
        profit_pct = (profit_isk / adjusted_cost) * 100.0
    else:
        profit_pct = 0.0

    # --- Minimal output + buy volume ---------------------------------------
    print("Deflection Shield Emitter")
    print(f"Profit/Loss: {profit_isk:,.2f} ISK")
    print(f"Profit/Loss: {profit_pct:.2f}%")
    print(f"Buy Order Volume: {buy_volume}")

if __name__ == "__main__":
    main()
