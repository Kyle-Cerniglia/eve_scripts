#!/usr/bin/env python3
"""
T2 Advanced Component profit checker for Jita 4-4.

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
MATERIAL_COST_MULTIPLIER = 0.9    # e.g. buy materials 10% under Jita sell
OVERHEAD_COST_MULTIPLIER = 1.15   # e.g. 15% overhead for taxes, fees, etc.

# ESI headers – PLEASE change user agent to something with your contact info
HEADERS = {
    "User-Agent": "T2ComponentProfitCalc/1.1 (your-email@example.com)",
    "Accept-Language": "en",
}

# ------------------------
# DATA: classic T2 advanced components (no neurolinks)
# Quantities are ME 0 (base BPO).
# ------------------------

COMPONENT_RECIPES: Dict[str, Dict[str, Dict[str, int]]] = {
    # Amarr
    "Antimatter Reactor Unit": {
        "materials": {
            "Tungsten Carbide": 9,
            "Fermionic Condensates": 2,
        }
    },
    "EM Pulse Generator": {
        "materials": {
            "Tungsten Carbide": 22,
            "Phenolic Composites": 7,
            "Nanotransistors": 2,
        }
    },
    "Fusion Thruster": {
        "materials": {
            "Tungsten Carbide": 13,
            "Phenolic Composites": 3,
            "Ferrogel": 1,
        }
    },
    "Laser Focusing Crystals": {
        "materials": {
            "Tungsten Carbide": 31,
            "Hypersynaptic Fibers": 1,
            "Fullerides": 11,
        }
    },
    "Linear Shield Emitter": {
        "materials": {
            "Tungsten Carbide": 22,
            "Ferrogel": 1,
            "Sylramic Fibers": 9,
        }
    },
    "Nanoelectrical Microprocessor": {
        "materials": {
            "Tungsten Carbide": 17,
            "Phenolic Composites": 6,
            "Terahertz Metamaterials": 2,
            "Nanotransistors": 2,
        }
    },
    "Radar Sensor Cluster": {
        "materials": {
            "Tungsten Carbide": 22,
            "Nanotransistors": 1,
            "Hypersynaptic Fibers": 2,
        }
    },
    "Tesseract Capacitor Unit": {
        "materials": {
            "Tungsten Carbide": 27,
            "Nanotransistors": 1,
            "Terahertz Metamaterials": 2,
            "Fullerides": 11,
        }
    },
    "Tungsten Carbide Armor Plate": {
        "materials": {
            "Tungsten Carbide": 44,
            "Sylramic Fibers": 11,
        }
    },

    # Caldari
    "Gravimetric Sensor Cluster": {
        "materials": {
            "Nanotransistors": 1,
            "Hypersynaptic Fibers": 2,
            "Titanium Carbide": 22,
        }
    },
    "Graviton Pulse Generator": {
        "materials": {
            "Phenolic Composites": 7,
            "Nanotransistors": 2,
            "Titanium Carbide": 22,
        }
    },
    "Graviton Reactor Unit": {
        "materials": {
            "Fermionic Condensates": 2,
            "Titanium Carbide": 9,
        }
    },
    "Magpulse Thruster": {
        "materials": {
            "Phenolic Composites": 3,
            "Ferrogel": 1,
            "Titanium Carbide": 13,
        }
    },
    "Quantum Microprocessor": {
        "materials": {
            "Phenolic Composites": 6,
            "Nanotransistors": 2,
            "Nonlinear Metamaterials": 2,
            "Titanium Carbide": 17,
        }
    },
    "Scalar Capacitor Unit": {
        "materials": {
            "Nanotransistors": 1,
            "Nonlinear Metamaterials": 2,
            "Fullerides": 11,
            "Titanium Carbide": 27,
        }
    },
    "Superconductor Rails": {
        "materials": {
            "Hypersynaptic Fibers": 1,
            "Fullerides": 11,
            "Titanium Carbide": 31,
        }
    },
    "Sustained Shield Emitter": {
        "materials": {
            "Ferrogel": 1,
            "Sylramic Fibers": 9,
            "Titanium Carbide": 22,
        }
    },
    "Titanium Diborite Armor Plate": {
        "materials": {
            "Sylramic Fibers": 11,
            "Titanium Carbide": 44,
        }
    },

    # Gallente
    "Crystalline Carbonide Armor Plate": {
        "materials": {
            "Sylramic Fibers": 11,
            "Crystalline Carbonide": 44,
        }
    },
    "Fusion Reactor Unit": {
        "materials": {
            "Fermionic Condensates": 2,
            "Crystalline Carbonide": 9,
        }
    },
    "Ion Thruster": {
        "materials": {
            "Phenolic Composites": 3,
            "Ferrogel": 1,
            "Crystalline Carbonide": 13,
        }
    },
    "Magnetometric Sensor Cluster": {
        "materials": {
            "Nanotransistors": 1,
            "Hypersynaptic Fibers": 2,
            "Crystalline Carbonide": 22,
        }
    },
    "Oscillator Capacitor Unit": {
        "materials": {
            "Nanotransistors": 1,
            "Photonic Metamaterials": 2,
            "Crystalline Carbonide": 27,
            "Fullerides": 11,
        }
    },
    "Particle Accelerator Unit": {
        "materials": {
            "Hypersynaptic Fibers": 1,
            "Crystalline Carbonide": 31,
            "Fullerides": 11,
        }
    },
    "Photon Microprocessor": {
        "materials": {
            "Phenolic Composites": 6,
            "Nanotransistors": 2,
            "Crystalline Carbonide": 17,
            "Photonic Metamaterials": 2,
        }
    },
    "Plasma Pulse Generator": {
        "materials": {
            "Phenolic Composites": 7,
            "Nanotransistors": 2,
            "Crystalline Carbonide": 22,
        }
    },
    "Pulse Shield Emitter": {
        "materials": {
            "Ferrogel": 1,
            "Sylramic Fibers": 9,
            "Crystalline Carbonide": 22,
        }
    },

    # Minmatar
    "Deflection Shield Emitter": {
        "materials": {
            "Fernite Carbide": 22,
            "Ferrogel": 1,
            "Sylramic Fibers": 9,
        }
    },
    "Electrolytic Capacitor Unit": {
        "materials": {
            "Fernite Carbide": 27,
            "Nanotransistors": 1,
            "Plasmonic Metamaterials": 2,
            "Fullerides": 11,
        }
    },
    "Fernite Carbide Composite Armor Plate": {
        "materials": {
            "Fernite Carbide": 44,
            "Sylramic Fibers": 11,
        }
    },
    "Ladar Sensor Cluster": {
        "materials": {
            "Fernite Carbide": 22,
            "Hypersynaptic Fibers": 2,
            "Nanotransistors": 1,
        }
    },
    "Nanomechanical Microprocessor": {
        "materials": {
            "Phenolic Composites": 6,
            "Fernite Carbide": 17,
            "Plasmonic Metamaterials": 2,
            "Nanotransistors": 2,
        }
    },
    "Nuclear Pulse Generator": {
        "materials": {
            "Phenolic Composites": 7,
            "Fernite Carbide": 22,
            "Nanotransistors": 2,
        }
    },
    "Nuclear Reactor Unit": {
        "materials": {
            "Fernite Carbide": 9,
            "Fermionic Condensates": 2,
        }
    },
    "Plasma Thruster": {
        "materials": {
            "Phenolic Composites": 3,
            "Fernite Carbide": 13,
            "Ferrogel": 1,
        }
    },
    "Thermonuclear Trigger Unit": {
        "materials": {
            "Fernite Carbide": 31,
            "Hypersynaptic Fibers": 1,
            "Fullerides": 11,
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
    header_component = "Component"
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
