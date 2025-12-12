#!/usr/bin/env python3
"""
Advanced Moon Materials profit checker for Jita 4-4.

- Uses ESI market data from The Forge.
- Material cost: lowest Jita 4-4 SELL orders.
- Output price: highest Jita 4-4 BUY orders.
- Assumes all blueprints are ME 0 (no material reduction).
- Applies configurable cost multipliers:
    MATERIAL_COST_MULTIPLIER (e.g. 0.9)
    OVERHEAD_COST_MULTIPLIER (e.g. 1.15)
- Prints one line per component in aligned columns:
    Component | Profit (ISK) | Profit % | Buy Vol
  sorted by most profitable percentage to least.
"""

import time
from typing import Dict, List, Optional

import requests

# ------------------------
# CONFIG
# ------------------------

ESI_BASE = "https://esi.evetech.net/latest"
DATASOURCE = "tranquility"

THE_FORGE_REGION_ID = 10000002
JITA_44_STATION_ID = 60003760  # Jita IV - Moon 4 - Caldari Navy Assembly Plant

# Change these to taste:
MATERIAL_COST_MULTIPLIER = 1    # e.g. buy materials 10% under Jita sell
OVERHEAD_COST_MULTIPLIER = 1.055   # e.g. 10% overhead for taxes, fees, etc.
REACTION_TAX = 1.1            # Percent tax rate for reactions (Cost index + structure tax)

# ESI headers – PLEASE change user agent to something with your contact info
HEADERS = {
    "User-Agent": "T2ComponentProfitCalc/1.1 (your-email@example.com)",
    "Accept-Language": "en",
}

# ------------------------
# DATA: T2 small rigs components and datacores
# Quantities are ME 0 (base BPO).
# ------------------------

COMPONENT_RECIPES: Dict[str, Dict[str, Dict[str, int]]] = {
    # Advanced Moon Materials
    "Crystalline Carbonide": {
        "materials": {
            "Crystallite Alloy": 100 / 10000,
            "Carbon Polymers": 100 / 10000,
            "Helium Fuel Block": 5 / 10000,
        }
    },
    "Fermionic Condensates": {
        "materials": {
            "Caesarium Cadmide": 100 / 200,
            "Dysporite": 100 / 200,
            "Fluxed Condensates": 100 / 200,
            "Prometium": 100 / 200,
            "Helium Fuel Block": 5 / 200,
        }
    },
    "Fernite Carbide": {
        "materials": {
            "Fernite Alloy": 100 / 10000,
            "Ceramic Powder": 100 / 10000,
            "Hydrogen Fuel Block": 5 / 10000,
        }
    },
    "Ferrogel": {
        "materials": {
            "Hexite": 100 / 400,
            "Hyperflurite": 100 / 400,
            "Ferrofluid": 100 / 400,
            "Prometium": 100 / 400,
            "Hydrogen Fuel Block": 5 / 400,
        }
    },
    "Fullerides": {
        "materials": {
            "Carbon Polymers": 100 / 3000,
            "Platinum Technite": 100 / 3000,
            "Nitrogen Fuel Block": 5 / 3000,
        }
    },
    "Hypersynaptic Fibers": {
        "materials": {
            "Solerium": 100 / 750,
            "Dysporite": 100 / 750,
            "Vanadium Hafnite": 100 / 750,
            "Oxygen Fuel Block": 5 / 750,
        }
    },
    "Nanotransistors": {
        "materials": {
            "Sulfuric Acid": 100 / 1500,
            "Platinum Technite": 100 / 1500,
            "Neo Mercurite": 100 / 1500,
            "Nitrogen Fuel Block": 5 / 1500,
        }
    },
    "Nonlinear Metamaterials": {
        "materials": {
            "Titanium Chromide": 100 / 300,
            "Ferrofluid": 100 / 300,
            "Nitrogen Fuel Block": 5 / 300,
        }
    },
    "Phenolic Composites": {
        "materials": {
            "Silicon Diborite": 100 / 2200,
            "Caesarium Cadmide": 100 / 2200,
            "Vanadium Hafnite": 100 / 2200,
            "Oxygen Fuel Block": 5 / 2200,
        }
    },
    "Photonic Metamaterials": {
        "materials": {
            "Crystallite Alloy": 100 / 300,
            "Thulium Hafnite": 100 / 300,
            "Oxygen Fuel Block": 5 / 300,
        }
    },
    "Plasmonic Metamaterials": {
        "materials": {
            "Fernite Alloy": 100 / 300,
            "Neo Mercurite": 100 / 300,
            "Hydrogen Fuel Block": 5 / 300,
        }
    },
    "Pressurized Oxidizers": {
        "materials": {
            "Carbon Polymers": 200 / 200,
            "Sulfuric Acid": 200 / 200,
            "Oxy-Organic Solvents": 1 / 200,
        }
    },
    "Reinforced Carbon Fiber": {
        "materials": {
            "Carbon Fiber": 10000 / 10000,
            "Oxy-Organic Solvents": 50 / 10000,
            "Thermosetting Polymer": 10000 / 10000,
        }
    },
    "Sylramic Fibers": {
        "materials": {
            "Ceramic Powder": 100 / 6000,
            "Hexite": 100 / 6000,
            "Helium Fuel Block": 5 / 6000,
        }
    },
    "Terahertz Metamaterials": {
        "materials": {
            "Rolled Tungsten Alloy": 100 / 300,
            "Promethium Mercurite": 100 / 300,
            "Helium Fuel Block": 5 / 300,
        }
    },
    "Titanium Carbide": {
        "materials": {
            "Titanium Chromide": 100 / 10000,
            "Silicon Diborite": 100 / 10000,
            "Oxygen Fuel Block": 5 / 10000,
        }
    },
    "Tungsten Carbide": {
        "materials": {
            "Rolled Tungsten Alloy": 100 / 10000,
            "Sulfuric Acid": 100 / 10000,
            "Nitrogen Fuel Block": 5 / 10000,
        }
    },
}


# ------------------------
# Helper functions
# ------------------------

def resolve_type_ids(names: List[str]) -> Dict[str, int]:
    """Resolve EVE item names -> type_ids via ESI /universe/ids/."""
    url = f"{ESI_BASE}/universe/ids/"
    resp = requests.post(
        url,
        params={"datasource": DATASOURCE},
        json=names,
        headers=HEADERS,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    mapping: Dict[str, int] = {}
    for entry in data.get("inventory_types", []):
        mapping[entry["name"]] = entry["id"]

    missing = sorted(set(names) - set(mapping))
    if missing:
        print("WARNING: Could not resolve type IDs for:")
        for name in missing:
            print("  -", name)

    return mapping


def get_best_order_in_jita(
    type_id: int,
    is_buy: bool,
    region_id: int = THE_FORGE_REGION_ID,
    jita_station_id: int = JITA_44_STATION_ID,
    max_pages: int = 10,
    cache: Optional[Dict[int, Dict]] = None,
) -> Optional[Dict]:
    """
    Get the best (highest buy / lowest sell) order in Jita 4-4 in The Forge.
    Optionally uses a simple cache dict keyed by type_id.
    """
    if cache is not None and type_id in cache:
        return cache[type_id]

    order_type = "buy" if is_buy else "sell"
    best_order: Optional[Dict] = None

    page = 1
    while page <= max_pages:
        url = f"{ESI_BASE}/markets/{region_id}/orders/"
        params = {
            "datasource": DATASOURCE,
            "order_type": order_type,
            "type_id": type_id,
            "page": page,
        }
        resp = requests.get(url, params=params, headers=HEADERS, timeout=30)

        # Handle rate limiting / transient issues a bit gracefully
        if resp.status_code in (420, 429, 500, 503, 504):
            print(f"ESI rate/temporary error ({resp.status_code}), sleeping briefly...")
            time.sleep(2)
            continue

        if resp.status_code == 204:
            break

        resp.raise_for_status()
        orders = resp.json()

        if not orders:
            break

        for order in orders:
            if order.get("location_id") != jita_station_id:
                continue

            price = order["price"]
            if best_order is None:
                best_order = order
            else:
                if is_buy:
                    # best buy = highest price
                    if price > best_order["price"]:
                        best_order = order
                else:
                    # best sell = lowest price
                    if price < best_order["price"]:
                        best_order = order

        x_pages = resp.headers.get("X-Pages")
        if not x_pages:
            break

        if page >= int(x_pages):
            break

        page += 1

    if cache is not None and best_order is not None:
        cache[type_id] = best_order

    return best_order


# ------------------------
# Core logic
# ------------------------

def compute_component_profit(
    component_name: str,
    recipe: Dict[str, Dict[str, int]],
    type_ids: Dict[str, int],
    buy_cache: Dict[int, Dict],
    sell_cache: Dict[int, Dict],
) -> Optional[Dict]:
    """
    For a single component:
      - Get best Jita BUY on the component (output price).
      - Get best Jita SELL on each material (input cost).
      - Assume ME 0 (base quantities).
      - Apply cost multipliers.
      - Return dict with profit data or None if something is missing.
    """
    if component_name not in type_ids:
        print(f"Skipping {component_name}: no type_id resolved.")
        return None

    product_type_id = type_ids[component_name]

    buy_order = get_best_order_in_jita(
        product_type_id, is_buy=True, cache=buy_cache
    )
    if not buy_order:
        print(f"Skipping {component_name}: no Jita 4-4 BUY orders.")
        return None

    materials = recipe["materials"]
    total_raw_material_cost = 0.0

    for mat_name, base_qty in materials.items():
        if mat_name not in type_ids:
            print(f"  Missing type_id for material {mat_name} in {component_name}, skipping item.")
            return None

        mat_type_id = type_ids[mat_name]
        sell_order = get_best_order_in_jita(
            mat_type_id, is_buy=False, cache=sell_cache
        )
        if not sell_order:
            print(f"  No Jita 4-4 SELL orders for material {mat_name} used in {component_name}, skipping item.")
            return None

        # ME 0: use base_qty directly
        total_raw_material_cost += base_qty * sell_order["price"]

    # Apply configurable cost multipliers
    effective_cost = total_raw_material_cost * MATERIAL_COST_MULTIPLIER * (OVERHEAD_COST_MULTIPLIER + REACTION_TAX - 1)

    sell_price = buy_order["price"]   # you sell to the highest Jita buy
    profit_isk = sell_price - effective_cost
    profit_pct = 0.0
    if effective_cost > 0:
        profit_pct = (profit_isk / effective_cost) * 100.0

    volume = buy_order.get("volume_remain", 0)

    return {
        "name": component_name,
        "profit_isk": profit_isk,
        "profit_pct": profit_pct,
        "buy_volume": volume,
        "sell_price": sell_price,
        "cost": effective_cost,
    }


def main():
    # Collect all names we need to resolve: components + all materials.
    all_names = set(COMPONENT_RECIPES.keys())
    for recipe in COMPONENT_RECIPES.values():
        all_names.update(recipe["materials"].keys())

    print("Resolving type IDs via ESI /universe/ids/ ...")
    type_ids = resolve_type_ids(sorted(all_names))

    buy_cache: Dict[int, Dict] = {}
    sell_cache: Dict[int, Dict] = {}

    results: List[Dict] = []

    print("Fetching market data and computing profits...\n")

    for name, recipe in COMPONENT_RECIPES.items():
        stats = compute_component_profit(
            name, recipe, type_ids, buy_cache, sell_cache
        )
        if stats is not None:
            results.append(stats)

    if not results:
        print("No results computed (missing market data or type IDs?).")
        return

    # Sort by profit percentage, descending
    results.sort(key=lambda r: r["profit_pct"], reverse=True)

    # Output: formatted columns
    header_component = "Adv Moon Mats"
    header_profit_isk = "Profit (ISK)"
    header_profit_pct = "Profit %"
    header_volume = "Buy Vol"

    print(f"{header_component:40} {header_profit_isk:>15} {header_profit_pct:>10} {header_volume:>10}")
    print("-" * 40 + " " + "-" * 15 + " " + "-" * 10 + " " + "-" * 10)

    for r in results:
        name = r["name"][:40]
        profit_isk = r["profit_isk"]
        profit_pct = r["profit_pct"]
        volume = r["buy_volume"]

        print(
            f"{name:40} "
            f"{profit_isk:15,.1f} "
            f"{profit_pct:10.1f} "
            f"{volume:10d}"
        )


if __name__ == "__main__":
    main()
