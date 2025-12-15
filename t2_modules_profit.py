#!/usr/bin/env python3
"""
T2 Modules profit checker for Jita 4-4.

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
OVERHEAD_COST_MULTIPLIER = 1.1   # e.g. 10% overhead for taxes, fees, etc.

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
    # Drone Upgrades
    "Drone Damage Amplifier II": {
        "materials": {
            "Datacore - Electronic Engineering": 2 / 0.468 / 10,
            "Datacore - Graviton Physics": 2 / 0.468 / 10,
            "Drone Damage Amplifier I": 1,
            "Morphite": 8,
            "Photon Microprocessor": 9,
            "Transmitter": 5,
            "Miniature Electronics": 5,
            "R.A.M.- Electronics": 1,
        }
    },
    "Drone Link Augmentor II": {
        "materials": {
            "Datacore - Electronic Engineering": 2 / 0.468 / 10,
            "Datacore - Graviton Physics": 2 / 0.468 / 10,
            "Drone Link Augmentor I": 1,
            "Morphite": 5,
            "Particle Accelerator Unit": 12,
            "Transmitter": 12,
            "R.A.M.- Electronics": 1,
        }
    },
    "Drone Navigation Computer II": {
        "materials": {
            "Datacore - Electronic Engineering": 2 / 0.468 / 10,
            "Datacore - Graviton Physics": 2 / 0.468 / 10,
            "Drone Navigation Computer I": 1,
            "Morphite": 5,
            "Particle Accelerator Unit": 12,
            "Transmitter": 12,
            "R.A.M.- Electronics": 1,
        }
    },
    "Fighter Support Unit II": {
        "materials": {
            "Datacore - Electronic Engineering": 4 / 0.468 / 5,
            "Datacore - Graviton Physics": 4 / 0.468 / 5,
            "Fighter Support Unit I": 1,
            "Morphite": 147,
            "Nanomechanical Microprocessor": 231,
            "Nanoelectrical Microprocessor": 217,
            "Quantum Microprocessor": 185,
            "Photon Microprocessor": 240,
            "Guidance Systems": 196,
            "R.A.M.- Electronics": 1,
        }
    },
    "Omnidirectional Tracking Enhancer II": {
        "materials": {
            "Datacore - Electronic Engineering": 2 / 0.468 / 10,
            "Datacore - Graviton Physics": 2 / 0.468 / 10,
            "Omnidirectional Tracking Enhancer I": 1,
            "Morphite": 5,
            "Nanoelectrical Microprocessor": 8,
            "Mechanical Parts": 8,
            "Miniature Electronics": 3,
            "R.A.M.- Electronics": 1,
        }
    },
    "Omnidirectional Tracking Link II": {
        "materials": {
            "Datacore - Electronic Engineering": 2 / 0.468 / 10,
            "Datacore - Graviton Physics": 2 / 0.468 / 10,
            "Omnidirectional Tracking Link I": 1,
            "Morphite": 5,
            "Partical Accelerator Unit": 12,
            "Transmitter": 12,
            "R.A.M.- Electronics": 1,
        }
    },
    # Electronic Warfare
    "Burst Jammer II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 2 / 0.47 / 10,
            "Datacore - Electronic Engineering": 2 / 0.47 / 10,
            "Burst Jammer I": 1,
            "Morphite": 6,
            "Gravimetric Sensor Cluster": 3,
            "Magnetometric Sensor Cluster": 3,
            "Ladar Sensor Cluster": 3,
            "Radar Sensor Cluster": 3,
            "Photon Microprocessor": 5,
            "Transmitter": 8,
            "Miniature Electronics": 9,
            "R.A.M.- Electronics": 1,
        }
    },
    "Gravimetric ECM II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 2 / 0.47 / 10,
            "Datacore - Electronic Engineering": 2 / 0.47 / 10,
            "Gravimetric ECM I": 1,
            "Morphite": 8,
            "Gravimetric Sensor Cluster": 9,
            "Quantum Microprocessor": 5,
            "Transmitter": 12,
            "Miniature Electronics": 9,
            "R.A.M.- Electronics": 1,
        }
    },
    "Ladar ECM II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 2 / 0.47 / 10,
            "Datacore - Electronic Engineering": 2 / 0.47 / 10,
            "Ladar ECM I": 1,
            "Morphite": 8,
            "Ladar Sensor Cluster": 9,
            "Nanomechanical Microprocessor": 5,
            "Transmitter": 12,
            "Miniature Electronics": 9,
            "R.A.M.- Electronics": 1,
        }
    },
    "Magnetometric ECM II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 2 / 0.47 / 10,
            "Datacore - Electronic Engineering": 2 / 0.47 / 10,
            "Magnetometric ECM I": 1,
            "Morphite": 8,
            "Magnetometric Sensor Cluster": 9,
            "Photon Microprocessor": 5,
            "Transmitter": 12,
            "Miniature Electronics": 9,
            "R.A.M.- Electronics": 1,
        }
    },
    "Multispectral ECM II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 2 / 0.47 / 10,
            "Datacore - Electronic Engineering": 2 / 0.47 / 10,
            "Multispectral ECM I": 1,
            "Morphite": 9,
            "Gravimetric Sensor Cluster": 3,
            "Magnetometric Sensor Cluster": 3,
            "Ladar Sensor Cluster": 3,
            "Radar Sensor Cluster": 3,
            "Photon Microprocessor": 5,
            "Transmitter": 12,
            "Miniature Electronics": 18,
            "R.A.M.- Electronics": 1,
        }
    },
    "Radar ECM II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 2 / 0.47 / 10,
            "Datacore - Electronic Engineering": 2 / 0.47 / 10,
            "Radar ECM I": 1,
            "Morphite": 8,
            "Magnetometric Sensor Cluster": 9,
            "Photon Microprocessor": 5,
            "Transmitter": 12,
            "Miniature Electronics": 9,
            "R.A.M.- Electronics": 1,
        }
    },
    "Signal Distortion Amplifier II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 2 / 0.47 / 10,
            "Datacore - Electronic Engineering": 2 / 0.47 / 10,
            "Signal Distortion Amplifier I": 1,
            "Morphite": 15,
            "Gravimetric Sensor Cluster": 3,
            "Magnetometric Sensor Cluster": 3,
            "Ladar Sensor Cluster": 3,
            "Radar Sensor Cluster": 3,
            "Photon Microprocessor": 5,
            "Transmitter": 14,
            "Miniature Electronics": 20,
            "R.A.M.- Electronics": 1,
        }
    },
    "Remote Sensor Dampener II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 1 / 0.479 / 10,
            "Datacore - Electronic Engineering": 1 / 0.479 / 10,
            "Remote Sensor Dampener I": 1,
            "Morphite": 8,
            "Gravimetric Sensor Cluster": 9,
            "Quantum Microprocessor": 5,
            "Transmitter": 8,
            "Miniature Electronics": 14,
            "R.A.M.- Electronics": 1,
        }
    },
    "Heavy Stasis Grappler II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 3 / 0.459 / 10,
            "Datacore - Graviton Physics": 3 / 0.459 / 10,
            "Heavy Stasis Grappler I": 1,
            "Morphite": 24,
            "Nanomechanical Microprocessor": 9,
            "Transmitter": 36,
            "Miniature Electronics": 24,
            "R.A.M.- Electronics": 1,
        }
    },
    "Stasis Webifier II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 2 / 0.459 / 10,
            "Datacore - Graviton Physics": 2 / 0.459 / 10,
            "Stasis Webifier I": 1,
            "Morphite": 8,
            "Nanomechanical Microprocessor": 3,
            "Transmitter": 12,
            "Miniature Electronics": 8,
            "R.A.M.- Electronics": 1,
        }
    },
    "Target Painter II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 2 / 0.459 / 10,
            "Datacore - Graviton Physics": 2 / 0.459 / 10,
            "Target Painter I": 1,
            "Morphite": 8,
            "Gravimetric Sensor Cluster": 9,
            "Quantum Microprocessor": 5,
            "Miniature Electronics": 5,
            "R.A.M.- Electronics": 1,
        }
    },
    "Warp Disruption Field Generator II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 2 / 0.459 / 10,
            "Datacore - Graviton Physics": 2 / 0.459 / 10,
            "Warp Disruption Field Generator I": 1,
            "Morphite": 6,
            "Ladar Sensor Cluster": 30,
            "Transmitter": 30,
            "R.A.M.- Electronics": 1,
        }
    },
    "Heavy Warp Disruptor II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 8 / 0.504 / 5,
            "Datacore - Graviton Physics": 8 / 0.504 / 5,
            "Heavy Warp Disruptor I": 1,
            "Morphite": 508,
            "Gravimetric Sensor Cluster": 413,
            "Quantum Microprocessor": 285,
            "Transmitter": 717,
            "Miniature Electronics": 457,
            "R.A.M.- Electronics": 3,
        }
    },
    "Warp Disruptor II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 2 / 0.459 / 10,
            "Datacore - Graviton Physics": 2 / 0.459 / 10,
            "Warp Disruptor I": 1,
            "Morphite": 8,
            "Gravimetric Sensor Cluster": 6,
            "Quantum Microprocessor": 5,
            "Transmitter": 15,
            "Miniature Electronics": 8,
            "R.A.M.- Electronics": 1,
        }
    },
    "Heavy Warp Scrambler II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 8 / 0.504 / 5,
            "Datacore - Graviton Physics": 8 / 0.504 / 5,
            "Heavy Warp Scrambler I": 1,
            "Morphite": 539,
            "Gravimetric Sensor Cluster": 167,
            "Quantum Microprocessor": 558,
            "Transmitter": 380,
            "Miniature Electronics": 790,
        }
    },
    "Warp Scrambler II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 2 / 0.459 / 10,
            "Datacore - Graviton Physics": 2 / 0.459 / 10,
            "Warp Scrambler I": 1,
            "Morphite": 8,
            "Gravimetric Sensor Cluster": 3,
            "Quantum Microprocessor": 9,
            "Transmitter": 8,
            "Miniature Electronics": 15,
            "R.A.M.- Electronics": 1,
        }
    },
    "Guidance Disruptor II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 2 / 0.47 / 10,
            "Datacore - Electronic Engineering": 2 / 0.47 / 10,
            "Guidance Disruptor I": 1,
            "Morphite": 8,
            "Magnetometric Sensor Cluster": 6,
            "Photon Microprocessor": 5,
            "Transmitter": 8,
            "Miniature Electronics": 14,
            "R.A.M.- Electronics": 1,
        }
    },
    "Tracking Disruptor II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 2 / 0.47 / 10,
            "Datacore - Electronic Engineering": 2 / 0.47 / 10,
            "Tracking Disruptor I": 1,
            "Morphite": 8,
            "Magnetometric Sensor Cluster": 6,
            "Photon Microprocessor": 5,
            "Transmitter": 8,
            "Miniature Electronics": 14,
            "R.A.M.- Electronics": 1,
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
    effective_cost = total_raw_material_cost * MATERIAL_COST_MULTIPLIER * OVERHEAD_COST_MULTIPLIER

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
    header_component = "T2 Modules"
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
            f"{profit_isk:15,.0f} "
            f"{profit_pct:10.1f} "
            f"{volume:10d}"
        )


if __name__ == "__main__":
    main()
