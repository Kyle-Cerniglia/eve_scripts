#!/usr/bin/env python3
"""
T2 Drones profit checker for Jita 4-4.

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
INVENTION_RATE = 0.428            # Percent chance for invention
BPC_RUNS = 10                      # Number of runs for a successful BPC invention

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
    # Heavy Attack Drones
    "Berserker II": {
        "materials": {
            "Datacore - Electronic Engineering": 3 / INVENTION_RATE / BPC_RUNS,
            "Datacore - Graviton Physics": 3 / INVENTION_RATE / BPC_RUNS,
            "Berserker I": 1,
            "Morphite": 6,
            "Thermonuclear Trigger Unit": 3,
            "Guidance Systems": 6,
            "Robotics": 6,
            "R.A.M.- Robotics": 1,
        }
    },
    "Ogre II": {
        "materials": {
            "Datacore - Electronic Engineering": 3 / INVENTION_RATE / BPC_RUNS,
            "Datacore - Graviton Physics": 3 / INVENTION_RATE / BPC_RUNS,
            "Ogre I": 1,
            "Morphite": 6,
            "Particle Accelerator Unit": 3,
            "Guidance Systems": 6,
            "Robotics": 6,
            "R.A.M.- Robotics": 1,
        }
    },
    "Praetor II": {
        "materials": {
            "Datacore - Electronic Engineering": 3 / INVENTION_RATE / BPC_RUNS,
            "Datacore - Graviton Physics": 3 / INVENTION_RATE / BPC_RUNS,
            "Praetor I": 1,
            "Morphite": 6,
            "Laser Focusing Crystals": 3,
            "Guidance Systems": 6,
            "Robotics": 6,
            "R.A.M.- Robotics": 1,
        }
    },
    "Wasp II": {
        "materials": {
            "Datacore - Electronic Engineering": 3 / INVENTION_RATE / BPC_RUNS,
            "Datacore - Graviton Physics": 3 / INVENTION_RATE / BPC_RUNS,
            "Wasp I": 1,
            "Morphite": 6,
            "Superconductor Rails": 3,
            "Guidance Systems": 6,
            "Robotics": 6,
            "R.A.M.- Robotics": 1,
        }
    },
    # Light Scout Drones
    "Acolyte II": {
        "materials": {
            "Datacore - Electronic Engineering": 1 / INVENTION_RATE / BPC_RUNS,
            "Datacore - Graviton Physics": 1 / INVENTION_RATE / BPC_RUNS,
            "Acolyte I": 1,
            "Morphite": 1,
            "Laser Focusing Crystals": 1,
            "Guidance Systems": 1,
            "Robotics": 1,
            "R.A.M.- Robotics": 1,
        }
    },
    "Hobgoblin II": {
        "materials": {
            "Datacore - Electronic Engineering": 1 / INVENTION_RATE / BPC_RUNS,
            "Datacore - Graviton Physics": 1 / INVENTION_RATE / BPC_RUNS,
            "Hobgoblin I": 1,
            "Morphite": 1,
            "Particle Accelerator Unit": 1,
            "Guidance Systems": 1,
            "Robotics": 1,
            "R.A.M.- Robotics": 1,
        }
    },
    "Hornet II": {
        "materials": {
            "Datacore - Electronic Engineering": 1 / INVENTION_RATE / BPC_RUNS,
            "Datacore - Graviton Physics": 1 / INVENTION_RATE / BPC_RUNS,
            "Hornet I": 1,
            "Morphite": 1,
            "Superconductor Rails": 1,
            "Guidance Systems": 1,
            "Robotics": 1,
            "R.A.M.- Robotics": 1,
        }
    },
    "Warrior II": {
        "materials": {
            "Datacore - Electronic Engineering": 1 / INVENTION_RATE / BPC_RUNS,
            "Datacore - Graviton Physics": 1 / INVENTION_RATE / BPC_RUNS,
            "Warrior I": 1,
            "Morphite": 1,
            "Thermonuclear Trigger Unit": 1,
            "Guidance Systems": 1,
            "Robotics": 1,
            "R.A.M.- Robotics": 1,
        }
    },
    # Medium Scout Drones
    "Hammerhead II": {
        "materials": {
            "Datacore - Electronic Engineering": 2 / INVENTION_RATE / BPC_RUNS,
            "Datacore - Graviton Physics": 2 / INVENTION_RATE / BPC_RUNS,
            "Hammerhead I": 1,
            "Morphite": 3,
            "Particle Accelerator Unit": 1,
            "Guidance Systems": 3,
            "Robotics": 3,
            "R.A.M.- Robotics": 1,
        }
    },
    "Infiltrator II": {
        "materials": {
            "Datacore - Electronic Engineering": 2 / INVENTION_RATE / BPC_RUNS,
            "Datacore - Graviton Physics": 2 / INVENTION_RATE / BPC_RUNS,
            "Infiltrator I": 1,
            "Morphite": 3,
            "Laser Focusing Crystals": 1,
            "Guidance Systems": 3,
            "Robotics": 3,
            "R.A.M.- Robotics": 1,
        }
    },
    "Valkyrie II": {
        "materials": {
            "Datacore - Electronic Engineering": 2 / INVENTION_RATE / BPC_RUNS,
            "Datacore - Graviton Physics": 2 / INVENTION_RATE / BPC_RUNS,
            "Valkyrie I": 1,
            "Morphite": 3,
            "Thermonuclear Trigger Unit": 1,
            "Guidance Systems": 3,
            "Robotics": 3,
            "R.A.M.- Robotics": 1,
        }
    },
    "Vespa II": {
        "materials": {
            "Datacore - Electronic Engineering": 2 / INVENTION_RATE / BPC_RUNS,
            "Datacore - Graviton Physics": 2 / INVENTION_RATE / BPC_RUNS,
            "Vespa I": 1,
            "Morphite": 3,
            "Superconductor Rails": 1,
            "Guidance Systems": 3,
            "Robotics": 3,
            "R.A.M.- Robotics": 1,
        }
    },
    # Sentry Drones
    "Bouncer II": {
        "materials": {
            "Datacore - Electronic Engineering": 3 / INVENTION_RATE / BPC_RUNS,
            "Datacore - Graviton Physics": 3 / INVENTION_RATE / BPC_RUNS,
            "Bouncer I": 1,
            "Morphite": 5,
            "Thermonuclear Trigger Unit": 3,
            "Guidance Systems": 5,
            "Robotics": 5,
            "R.A.M.- Robotics": 1,
        }
    },
    "Curator II": {
        "materials": {
            "Datacore - Electronic Engineering": 3 / INVENTION_RATE / BPC_RUNS,
            "Datacore - Graviton Physics": 3 / INVENTION_RATE / BPC_RUNS,
            "Curator I": 1,
            "Morphite": 5,
            "Laser Focusing Crystals": 3,
            "Guidance Systems": 5,
            "Robotics": 5,
            "R.A.M.- Robotics": 1,
        }
    },
    "Garde II": {
        "materials": {
            "Datacore - Electronic Engineering": 3 / INVENTION_RATE / BPC_RUNS,
            "Datacore - Graviton Physics": 3 / INVENTION_RATE / BPC_RUNS,
            "Garde I": 1,
            "Morphite": 5,
            "Particle Accelerator Unit": 3,
            "Guidance Systems": 5,
            "Robotics": 5,
            "R.A.M.- Robotics": 1,
        }
    },
    "Warden II": {
        "materials": {
            "Datacore - Electronic Engineering": 3 / INVENTION_RATE / BPC_RUNS,
            "Datacore - Graviton Physics": 3 / INVENTION_RATE / BPC_RUNS,
            "Warden I": 1,
            "Morphite": 5,
            "Superconductor Rails": 3,
            "Guidance Systems": 5,
            "Robotics": 5,
            "R.A.M.- Robotics": 1,
        }
    },
    # Light Fighters
    "Dragonfly II": {
        "materials": {
            "Datacore - Electronic Engineering": 3 / INVENTION_RATE / BPC_RUNS,
            "Datacore - Graviton Physics": 3 / INVENTION_RATE / BPC_RUNS,
            "Dragonfly I": 1,
            "Morphite": 12,
            "Magpulse Thruster": 12,
            "Gravimetric Sensor Cluster": 12,
            "Graviton Reactor Unit": 16,
            "Superconductor Rails": 12,
            "Guidance Systems": 12,
            "R.A.M.- Starship Tech": 3,
        }
    },
    "Einherji II": {
        "materials": {
            "Datacore - Electronic Engineering": 3 / INVENTION_RATE / BPC_RUNS,
            "Datacore - Graviton Physics": 3 / INVENTION_RATE / BPC_RUNS,
            "Einherji I": 1,
            "Morphite": 12,
            "Plasma Thruster": 12,
            "Ladar Sensor Cluster": 12,
            "Nuclear Reactor Unit": 16,
            "Thermonuclear Trigger Unit": 12,
            "Guidance Systems": 12,
            "R.A.M.- Starship Tech": 3,
        }
    },
    "Equite II": {
        "materials": {
            "Datacore - Electronic Engineering": 3 / INVENTION_RATE / BPC_RUNS,
            "Datacore - Graviton Physics": 3 / INVENTION_RATE / BPC_RUNS,
            "Equite I": 1,
            "Morphite": 10,
            "Phenolic Composites": 40,
            "Fusion Thruster": 20,
            "Radar Sensor Cluster": 8,
            "Antimatter Reactor Unit": 12,
            "Guidance Systems": 8,
            "R.A.M.- Starship Tech": 3,
        }
    },
    "Firbolg II": {
        "materials": {
            "Datacore - Electronic Engineering": 3 / INVENTION_RATE / BPC_RUNS,
            "Datacore - Graviton Physics": 3 / INVENTION_RATE / BPC_RUNS,
            "Firbolg I": 1,
            "Morphite": 12,
            "Ion Thruster": 12,
            "Magnetometric Sensor Cluster": 12,
            "Fusion Reactor Unit": 16,
            "Particle Accelerator Unit": 12,
            "Guidance Systems": 12,
            "R.A.M.- Starship Tech": 3,
        }
    },
    "Gram II": {
        "materials": {
            "Datacore - Electronic Engineering": 3 / INVENTION_RATE / BPC_RUNS,
            "Datacore - Graviton Physics": 3 / INVENTION_RATE / BPC_RUNS,
            "Gram I": 1,
            "Morphite": 10,
            "Phenolic Composites": 40,
            "Plasma Thruster": 20,
            "Ladar Sensor Cluster": 8,
            "Nuclear Reactor Unit": 12,
            "Guidance Systems": 8,
            "R.A.M.- Starship Tech": 3,
        }
    },
    "Locust II": {
        "materials": {
            "Datacore - Electronic Engineering": 3 / INVENTION_RATE / BPC_RUNS,
            "Datacore - Graviton Physics": 3 / INVENTION_RATE / BPC_RUNS,
            "Locust I": 1,
            "Morphite": 10,
            "Phenolic Composites": 40,
            "Magpulse Thruster": 20,
            "Gravimetric Sensor Cluster": 8,
            "Graviton Reactor Unit": 12,
            "Guidance Systems": 8,
            "R.A.M.- Starship Tech": 3,
        }
    },
    "Satyr II": {
        "materials": {
            "Datacore - Electronic Engineering": 3 / INVENTION_RATE / BPC_RUNS,
            "Datacore - Graviton Physics": 3 / INVENTION_RATE / BPC_RUNS,
            "Satyr I": 1,
            "Morphite": 10,
            "Phenolic Composites": 40,
            "Ion Thruster": 20,
            "Magnetometric Sensor Cluster": 8,
            "Fusion Reactor Unit": 12,
            "Guidance Systems": 8,
            "R.A.M.- Starship Tech": 3,
        }
    },
    # Support Fighters
    "Cenobite II": {
        "materials": {
            "Datacore - Electronic Engineering": 3 / INVENTION_RATE / BPC_RUNS,
            "Datacore - Graviton Physics": 3 / INVENTION_RATE / BPC_RUNS,
            "Cenobite I": 1,
            "Morphite": 24,
            "Fusion Thruster": 22,
            "Radar Sensor Cluster": 28,
            "Nanoelectrical Microprocessor": 40,
            "Antimatter Reactor Unit": 38,
            "Tesseract Capacitor Unit": 36,
            "R.A.M.- Starship Tech": 3,
        }
    },
    "Dromi II": {
        "materials": {
            "Datacore - Electronic Engineering": 3 / INVENTION_RATE / BPC_RUNS,
            "Datacore - Graviton Physics": 3 / INVENTION_RATE / BPC_RUNS,
            "Dromi I": 1,
            "Morphite": 24,
            "Plasma Thruster": 22,
            "Ladar Sensor Cluster": 28,
            "Nanomechanical Microprocessor": 40,
            "Nuclear Reactor Unit": 38,
            "Electrolytic Capacitor Unit": 36,
            "R.A.M.- Starship Tech": 3,
        }
    },
    "Scarab II": {
        "materials": {
            "Datacore - Electronic Engineering": 3 / INVENTION_RATE / BPC_RUNS,
            "Datacore - Graviton Physics": 3 / INVENTION_RATE / BPC_RUNS,
            "Scarab I": 1,
            "Morphite": 24,
            "Magpulse Thruster": 22,
            "Gravimetric Sensor Cluster": 28,
            "Quantum Microprocessor": 40,
            "Graviton Reactor Unit": 38,
            "Scalar Capacitor Unit": 36,
            "R.A.M.- Starship Tech": 3,
        }
    },
    "Siren II": {
        "materials": {
            "Datacore - Electronic Engineering": 3 / INVENTION_RATE / BPC_RUNS,
            "Datacore - Graviton Physics": 3 / INVENTION_RATE / BPC_RUNS,
            "Siren I": 1,
            "Morphite": 24,
            "Ion Thruster": 22,
            "Magnetometric Sensor Cluster": 28,
            "Photon Microprocessor": 40,
            "Fusion Reactor Unit": 38,
            "Oscillator Capacitor Unit": 36,
            "R.A.M.- Starship Tech": 3,
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
    header_component = "T2 Drones/Fighters"
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
