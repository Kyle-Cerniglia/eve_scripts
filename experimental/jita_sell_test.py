#!/usr/bin/env python3
"""
Get highest Jita buy order for 'Deflection Shield Emitter'.

Uses ESI public endpoint:
  GET /markets/{region_id}/orders/

Region: The Forge (10000002)
System: Jita (30000142)
Item:  Deflection Shield Emitter (type_id = 11555)
"""

import sys
import requests

# Constants
TYPE_ID = 11555        # Deflection Shield Emitter
REGION_ID = 10000002   # The Forge
JITA_SYSTEM_ID = 30000142  # Jita system id
ESI_URL = f"https://esi.evetech.net/latest/markets/{REGION_ID}/orders/"

# Set a descriptive User-Agent per ESI guidelines
HEADERS = {
    "User-Agent": "JitaDeflectionShieldEmitterChecker/1.0 (youremail@example.com)"
}


def fetch_orders_for_type(type_id: int):
    """
    Fetch all market orders in the region for the given type_id.

    We use order_type=all and then filter is_buy_order in code.
    In practice, when type_id is provided, ESI typically returns
    all matching orders in a single page, but we handle X-Pages
    just in case.
    """
    all_orders = []

    params = {
        "datasource": "tranquility",
        "order_type": "all",  # get both, we'll filter locally
        "type_id": type_id,
        "page": 1,
    }

    while True:
        resp = requests.get(ESI_URL, headers=HEADERS, params=params, timeout=10)
        resp.raise_for_status()

        page_orders = resp.json()
        all_orders.extend(page_orders)

        # Pagination: X-Pages header is only set when order_type=all
        x_pages = resp.headers.get("X-Pages")
        if not x_pages:
            break  # single page
        if params["page"] >= int(x_pages):
            break

        params["page"] += 1

    return all_orders


def get_highest_jita_buy_order():
    """Return the highest-priced Jita buy order dict, or None if none exist."""
    orders = fetch_orders_for_type(TYPE_ID)

    # Filter to buy orders in Jita system
    jita_buy_orders = [
        o for o in orders
        if o.get("is_buy_order") is True
        and o.get("system_id") == JITA_SYSTEM_ID
    ]

    if not jita_buy_orders:
        return None

    # Highest buy price
    best_order = max(jita_buy_orders, key=lambda o: o["price"])
    return best_order


def main():
    try:
        best = get_highest_jita_buy_order()
    except requests.RequestException as e:
        print(f"Error talking to ESI: {e}", file=sys.stderr)
        sys.exit(1)

    if best is None:
        print("No buy orders for 'Deflection Shield Emitter' found in Jita.")
        sys.exit(0)

    price = best["price"]
    quantity = best["volume_remain"]  # remaining quantity on the order

    print("Highest Jita buy order for 'Deflection Shield Emitter':")
    print(f"  Price:    {price:,.2f} ISK")
    print(f"  Quantity: {quantity}")


if __name__ == "__main__":
    main()
