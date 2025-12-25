#!/usr/bin/env python3
"""
T2 Medium Rigs profit checker for Jita 4-4.

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
INVENTION_RATE = 0.435            # Percent chance for invention

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
    # Armor Rigs
    "Medium Auxiliary Nano Pump II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 2 / INVENTION_RATE,
            "Datacore - Nanite Engineering": 2 / INVENTION_RATE,
            "Nanite Compound": 3,
            "Interface Circuit": 5,
            "Intact Armor Plates": 5,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "Medium EM Armor Reinforcer II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 2 / INVENTION_RATE,
            "Datacore - Nanite Engineering": 2 / INVENTION_RATE,
            "Nanite Compound": 1,
            "Interface Circuit": 5,
            "Intact Armor Plates": 3,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "Medium Explosive Armor Reinforcer II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 2 / INVENTION_RATE,
            "Datacore - Nanite Engineering": 2 / INVENTION_RATE,
            "Nanite Compound": 1,
            "Interface Circuit": 5,
            "Intact Armor Plates": 3,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "Medium Kinetic Armor Reinforcer II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 2 / INVENTION_RATE,
            "Datacore - Nanite Engineering": 2 / INVENTION_RATE,
            "Nanite Compound": 1,
            "Interface Circuit": 5,
            "Intact Armor Plates": 3,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "Medium Nanobot Accelerator II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 2 / INVENTION_RATE,
            "Datacore - Nanite Engineering": 2 / INVENTION_RATE,
            "Nanite Compound": 3,
            "Interface Circuit": 5,
            "Intact Armor Plates": 5,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "Medium Remote Repair Augmentor II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 2 / INVENTION_RATE,
            "Datacore - Nanite Engineering": 2 / INVENTION_RATE,
            "Nanite Compound": 3,
            "Interface Circuit": 5,
            "Intact Armor Plates": 5,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "Medium Thermal Armor Reinforcer II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 2 / INVENTION_RATE,
            "Datacore - Nanite Engineering": 2 / INVENTION_RATE,
            "Nanite Compound": 1,
            "Interface Circuit": 5,
            "Intact Armor Plates": 3,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "Medium Transverse Bulkhead II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 2 / INVENTION_RATE,
            "Datacore - Nanite Engineering": 2 / INVENTION_RATE,
            "Nanite Compound": 5,
            "Single-crystal Superalloy I-beam": 3,
            "Interface Circuit": 3,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "Medium Trimark Armor Pump II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 2 / INVENTION_RATE,
            "Datacore - Nanite Engineering": 2 / INVENTION_RATE,
            "Nanite Compound": 3,
            "Interface Circuit": 5,
            "Intact Armor Plates": 3,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    # Astronautic Rigs
    "Medium Auxiliary Thrusters II": {
        "materials": {
            "Datacore - Molecular Engineering": 2 / INVENTION_RATE,
            "Datacore - Nanite Engineering": 2 / INVENTION_RATE,
            "Micro Circuit": 5,
            "Logic Circuit": 6,
            "Impetus Console": 1,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "Medium Cargohold Optimization II": {
        "materials": {
            "Datacore - Molecular Engineering": 2 / INVENTION_RATE,
            "Datacore - Nanite Engineering": 2 / INVENTION_RATE,
            "Single-crystal Superalloy I-beam": 6,
            "Power Circuit": 5,
            "Interface Circuit": 8,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "Medium Dynamic Fuel Valve II": {
        "materials": {
            "Datacore - Molecular Engineering": 2 / INVENTION_RATE,
            "Datacore - Nanite Engineering": 2 / INVENTION_RATE,
            "Single-crystal Superalloy I-beam": 1,
            "Power Circuit": 3,
            "Logic Circuit": 1,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "Medium Engine Thermal Shielding II": {
        "materials": {
            "Datacore - Molecular Engineering": 2 / INVENTION_RATE,
            "Datacore - Nanite Engineering": 2 / INVENTION_RATE,
            "Single-crystal Superalloy I-beam": 3,
            "Power Circuit": 5,
            "Interface Circuit": 5,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "Medium Hyperspatial Velocity Optimizer II": {
        "materials": {
            "Datacore - Molecular Engineering": 2 / INVENTION_RATE,
            "Datacore - Nanite Engineering": 2 / INVENTION_RATE,
            "Micro Circuit": 5,
            "Logic Circuit": 6,
            "Impetus Console": 5,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "Medium Low Friction Nozzle Joints II": {
        "materials": {
            "Datacore - Molecular Engineering": 2 / INVENTION_RATE,
            "Datacore - Nanite Engineering": 2 / INVENTION_RATE,
            "Micro Circuit": 5,
            "Logic Circuit": 6,
            "Impetus Console": 1,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "Medium Polycarbon Engine Housing II": {
        "materials": {
            "Datacore - Molecular Engineering": 2 / INVENTION_RATE,
            "Datacore - Nanite Engineering": 2 / INVENTION_RATE,
            "Single-crystal Superalloy I-beam": 6,
            "Power Circuit": 5,
            "Interface Circuit": 6,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "Medium Warp Core Optimizer II": {
        "materials": {
            "Datacore - Molecular Engineering": 2 / INVENTION_RATE,
            "Datacore - Nanite Engineering": 2 / INVENTION_RATE,
            "Micro Circuit": 5,
            "Logic Circuit": 6,
            "Impetus Console": 5,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    # Drone Rigs
    "Medium Drone Control Range Augmentor II": {
        "materials": {
            "Datacore - Electronic Engineering": 2 / INVENTION_RATE,
            "Datacore - Mechanical Engineering": 2 / INVENTION_RATE,
            "Drone Transceiver": 3,
            "Power Circuit": 5,
            "Logic Circuit": 5,
            "R.A.M.- Robotics": 1,
        }
    },
    "Medium Drone Durability Enhancer II": {
        "materials": {
            "Datacore - Electronic Engineering": 2 / INVENTION_RATE,
            "Datacore - Mechanical Engineering": 2 / INVENTION_RATE,
            "Drone Transceiver": 5,
            "Power Circuit": 6,
            "Logic Circuit": 6,
            "R.A.M.- Robotics": 1,
        }
    },
    "Medium Drone Mining Augmentor II": {
        "materials": {
            "Datacore - Electronic Engineering": 2 / INVENTION_RATE,
            "Datacore - Mechanical Engineering": 2 / INVENTION_RATE,
            "Drone Transceiver": 5,
            "Power Circuit": 6,
            "Logic Circuit": 6,
            "R.A.M.- Robotics": 1,
        }
    },
    "Medium Drone Repair Augmentor II": {
        "materials": {
            "Datacore - Electronic Engineering": 2 / INVENTION_RATE,
            "Datacore - Mechanical Engineering": 2 / INVENTION_RATE,
            "Drone Transceiver": 3,
            "Power Circuit": 5,
            "Logic Circuit": 5,
            "R.A.M.- Robotics": 1,
        }
    },
    "Medium Drone Scope Chip II": {
        "materials": {
            "Datacore - Electronic Engineering": 2 / INVENTION_RATE,
            "Datacore - Mechanical Engineering": 2 / INVENTION_RATE,
            "Drone Transceiver": 3,
            "Power Circuit": 5,
            "Logic Circuit": 5,
            "R.A.M.- Robotics": 1,
        }
    },
    "Medium Drone Speed Augmentor II": {
        "materials": {
            "Datacore - Electronic Engineering": 2 / INVENTION_RATE,
            "Datacore - Mechanical Engineering": 2 / INVENTION_RATE,
            "Drone Transceiver": 5,
            "Power Circuit": 5,
            "Logic Circuit": 5,
            "R.A.M.- Robotics": 1,
        }
    },
    "Medium Sentry Damage Augmentor II": {
        "materials": {
            "Datacore - Electronic Engineering": 2 / INVENTION_RATE,
            "Datacore - Mechanical Engineering": 2 / INVENTION_RATE,
            "Drone Transceiver": 6,
            "Power Circuit": 6,
            "Logic Circuit": 6,
            "R.A.M.- Robotics": 1,
        }
    },
    "Medium Stasis Drone Augmentor II": {
        "materials": {
            "Datacore - Electronic Engineering": 2 / INVENTION_RATE,
            "Datacore - Mechanical Engineering": 2 / INVENTION_RATE,
            "Drone Transceiver": 6,
            "Power Circuit": 8,
            "Logic Circuit": 8,
            "R.A.M.- Robotics": 1,
        }
    },
    # Electronics Superiority Rigs
    "Medium Inverted Signal Field Projector II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 2 / INVENTION_RATE,
            "Datacore - Electronic Engineering": 2 / INVENTION_RATE,
            "Artificial Neural Network": 3,
            "Power Circuit": 5,
            "Interface Circuit": 6,
            "R.A.M.- Electronics": 1,
            "Miniature Electronics": 12,
        }
    },
    "Medium Particle Dispersion Augmentor II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 2 / INVENTION_RATE,
            "Datacore - Electronic Engineering": 2 / INVENTION_RATE,
            "Artificial Neural Network": 3,
            "Power Circuit": 5,
            "Interface Circuit": 5,
            "R.A.M.- Electronics": 1,
            "Miniature Electronics": 12,
        }
    },
    "Medium Particle Dispersion Projector II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 2 / INVENTION_RATE,
            "Datacore - Electronic Engineering": 2 / INVENTION_RATE,
            "Artificial Neural Network": 3,
            "Micro Circuit": 5,
            "Logic Circuit": 6,
            "R.A.M.- Electronics": 1,
            "Miniature Electronics": 12,
        }
    },
    "Medium Signal Disruption Amplifier II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 2 / INVENTION_RATE,
            "Datacore - Electronic Engineering": 2 / INVENTION_RATE,
            "Artificial Neural Network": 5,
            "Power Circuit": 5,
            "Conductive Thermoplastic": 1,
            "R.A.M.- Electronics": 1,
        }
    },
    "Medium Targeting Systems Stabilizer II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 2 / INVENTION_RATE,
            "Datacore - Electronic Engineering": 2 / INVENTION_RATE,
            "Artificial Neural Network": 5,
            "Micro Circuit": 6,
            "Logic Circuit": 6,
            "R.A.M.- Electronics": 1,
            "Miniature Electronics": 12,
        }
    },
    "Medium Tracking Diagnostic Subroutines II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 2 / INVENTION_RATE,
            "Datacore - Electronic Engineering": 2 / INVENTION_RATE,
            "Artificial Neural Network": 3,
            "Micro Circuit": 5,
            "Logic Circuit": 6,
            "R.A.M.- Electronics": 1,
            "Miniature Electronics": 12,
        }
    },
    # Energy Weapon Rigs
    "Medium Algid Energy Administrations Unit II": {
        "materials": {
            "Datacore - High Energy Physics": 2 / INVENTION_RATE,
            "Datacore - Laser Physics": 2 / INVENTION_RATE,
            "Current Pump": 5,
            "Micro Circuit": 5,
            "Interface Circuit": 6,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Medium Energy Ambit Extension II": {
        "materials": {
            "Datacore - High Energy Physics": 2 / INVENTION_RATE,
            "Datacore - Laser Physics": 2 / INVENTION_RATE,
            "Current Pump": 3,
            "Micro Circuit": 5,
            "Interface Circuit": 6,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Medium Energy Burst Aerator II": {
        "materials": {
            "Datacore - High Energy Physics": 2 / INVENTION_RATE,
            "Datacore - Laser Physics": 2 / INVENTION_RATE,
            "Current Pump": 6,
            "Micro Circuit": 5,
            "Interface Circuit": 8,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Medium Energy Collision Accelerator II": {
        "materials": {
            "Datacore - High Energy Physics": 2 / INVENTION_RATE,
            "Datacore - Laser Physics": 2 / INVENTION_RATE,
            "Current Pump": 6,
            "Micro Circuit": 5,
            "Interface Circuit": 8,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Medium Energy Discharge Elutriation II": {
        "materials": {
            "Datacore - High Energy Physics": 2 / INVENTION_RATE,
            "Datacore - Laser Physics": 2 / INVENTION_RATE,
            "Current Pump": 1,
            "Micro Circuit": 3,
            "Interface Circuit": 3,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Medium Energy Locus Coordinator II": {
        "materials": {
            "Datacore - High Energy Physics": 2 / INVENTION_RATE,
            "Datacore - Laser Physics": 2 / INVENTION_RATE,
            "Current Pump": 3,
            "Micro Circuit": 5,
            "Interface Circuit": 6,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Medium Energy Metastasis Adjuster II": {
        "materials": {
            "Datacore - High Energy Physics": 2 / INVENTION_RATE,
            "Datacore - Laser Physics": 2 / INVENTION_RATE,
            "Current Pump": 3,
            "Micro Circuit": 5,
            "Interface Circuit": 6,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    # Engineering Rigs
    "Medium Ancillary Current Router II": {
        "materials": {
            "Datacore - High Energy Physics": 2 / INVENTION_RATE,
            "Datacore - Quantum Physics": 2 / INVENTION_RATE,
            "Power Conduit": 3,
            "Power Circuit": 14,
            "Logic Circuit": 14,
            "R.A.M.- Energy Tech": 1,
        }
    },
    "Medium Capacitor Control Circuit II": {
        "materials": {
            "Datacore - High Energy Physics": 2 / INVENTION_RATE,
            "Datacore - Quantum Physics": 2 / INVENTION_RATE,
            "Power Circuit": 5,
            "Logic Circuit": 5,
            "Capacitor Console": 1,
            "R.A.M.- Energy Tech": 1,
        }
    },
    "Medium Egress Port Maximizer II": {
        "materials": {
            "Datacore - High Energy Physics": 2 / INVENTION_RATE,
            "Datacore - Quantum Physics": 2 / INVENTION_RATE,
            "Power Conduit": 3,
            "Power Circuit": 5,
            "Interface Circuit": 5,
            "R.A.M.- Energy Tech": 1,
        }
    },
    "Medium Liquid Cooled Electronics II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 2 / INVENTION_RATE,
            "Datacore - Electronic Engineering": 2 / INVENTION_RATE,
            "Artificial Neural Network": 5,
            "Power Circuit": 6,
            "Conductive Thermoplastic": 3,
            "R.A.M.- Electronics": 1,
        }
    },
    "Medium Powergrid Subroutine Maximizer II": {
        "materials": {
            "Datacore - High Energy Physics": 2 / INVENTION_RATE,
            "Datacore - Quantum Physics": 2 / INVENTION_RATE,
            "Power Conduit": 3,
            "Power Circuit": 5,
            "Interface Circuit": 5,
            "R.A.M.- Energy Tech": 1,
        }
    },
    "Medium Processor Overclocking Unit II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 2 / INVENTION_RATE,
            "Datacore - Electronic Engineering": 2 / INVENTION_RATE,
            "Artificial Neural Network": 5,
            "Power Circuit": 6,
            "Conductive Thermoplastic": 3,
            "R.A.M.- Electronics": 1,
        }
    },
    "Medium Semiconductor Memory Cell II": {
        "materials": {
            "Datacore - High Energy Physics": 2 / INVENTION_RATE,
            "Datacore - Quantum Physics": 2 / INVENTION_RATE,
            "Power Circuit": 9,
            "Logic Circuit": 9,
            "Capacitor Console": 3,
            "R.A.M.- Energy Tech": 1,
        }
    },
    # Hybrid Weapon Rigs
    "Medium Algid Hybrid Administrations Unit II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 2 / INVENTION_RATE,
            "Datacore - Mechanical Engineering": 2 / INVENTION_RATE,
            "Lorentz Fluid": 5,
            "Micro Circuit": 5,
            "Interface Circuit": 6,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Medium Hybrid Ambit Extension II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 2 / INVENTION_RATE,
            "Datacore - Mechanical Engineering": 2 / INVENTION_RATE,
            "Lorentz Fluid": 3,
            "Micro Circuit": 5,
            "Interface Circuit": 6,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Medium Hybrid Burst Aerator II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 2 / INVENTION_RATE,
            "Datacore - Mechanical Engineering": 2 / INVENTION_RATE,
            "Lorentz Fluid": 6,
            "Micro Circuit": 5,
            "Interface Circuit": 8,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Medium Hybrid Collision Accelerator II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 2 / INVENTION_RATE,
            "Datacore - Mechanical Engineering": 2 / INVENTION_RATE,
            "Lorentz Fluid": 6,
            "Micro Circuit": 5,
            "Interface Circuit": 8,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Medium Hybrid Discharge Elutriation II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 2 / INVENTION_RATE,
            "Datacore - Mechanical Engineering": 2 / INVENTION_RATE,
            "Lorentz Fluid": 1,
            "Micro Circuit": 3,
            "Interface Circuit": 3,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Medium Hybrid Locus Coordinator II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 2 / INVENTION_RATE,
            "Datacore - Mechanical Engineering": 2 / INVENTION_RATE,
            "Lorentz Fluid": 3,
            "Micro Circuit": 5,
            "Interface Circuit": 6,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Medium Hybrid Metastasis Adjuster II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 2 / INVENTION_RATE,
            "Datacore - Mechanical Engineering": 2 / INVENTION_RATE,
            "Lorentz Fluid": 3,
            "Micro Circuit": 5,
            "Interface Circuit": 6,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    # Missile Launcher Rigs
    "Medium Bay Loading Accelerator II": {
        "materials": {
            "Datacore - Rocket Science": 2 / INVENTION_RATE,
            "Datacore - Mechanical Engineering": 2 / INVENTION_RATE,
            "Telemetry Processor": 6,
            "Power Circuit": 5,
            "Logic Circuit": 8,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Medium Hydraulic Bay Thrusters II": {
        "materials": {
            "Datacore - Rocket Science": 2 / INVENTION_RATE,
            "Datacore - Mechanical Engineering": 2 / INVENTION_RATE,
            "Telemetry Processor": 3,
            "Power Circuit": 6,
            "Logic Circuit": 6,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Medium Rocket Fuel Cache Partition II": {
        "materials": {
            "Datacore - Rocket Science": 2 / INVENTION_RATE,
            "Datacore - Mechanical Engineering": 2 / INVENTION_RATE,
            "Telemetry Processor": 3,
            "Power Circuit": 6,
            "Logic Circuit": 6,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Medium Warhead Calefaction Catalyst II": {
        "materials": {
            "Datacore - Rocket Science": 2 / INVENTION_RATE,
            "Datacore - Mechanical Engineering": 2 / INVENTION_RATE,
            "Telemetry Processor": 6,
            "Power Circuit": 5,
            "Logic Circuit": 8,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Medium Warhead Flare Catalyst II": {
        "materials": {
            "Datacore - Rocket Science": 2 / INVENTION_RATE,
            "Datacore - Mechanical Engineering": 2 / INVENTION_RATE,
            "Telemetry Processor": 3,
            "Power Circuit": 5,
            "Logic Circuit": 6,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Medium Warhead Rigor Catalyst II": {
        "materials": {
            "Datacore - Rocket Science": 2 / INVENTION_RATE,
            "Datacore - Mechanical Engineering": 2 / INVENTION_RATE,
            "Telemetry Processor": 3,
            "Power Circuit": 6,
            "Logic Circuit": 6,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    # Projectile Weapon Rigs
    "Medium Projectile Ambit Extension II": {
        "materials": {
            "Datacore - Nuclear Physics": 2 / INVENTION_RATE,
            "Datacore - Mechanical Engineering": 2 / INVENTION_RATE,
            "Trigger Unit": 3,
            "Micro Circuit": 5,
            "Interface Circuit": 6,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Medium Projectile Burst Aerator II": {
        "materials": {
            "Datacore - Nuclear Physics": 2 / INVENTION_RATE,
            "Datacore - Mechanical Engineering": 2 / INVENTION_RATE,
            "Trigger Unit": 6,
            "Micro Circuit": 5,
            "Interface Circuit": 8,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Medium Projectile Collision Accelerator II": {
        "materials": {
            "Datacore - Nuclear Physics": 2 / INVENTION_RATE,
            "Datacore - Mechanical Engineering": 2 / INVENTION_RATE,
            "Trigger Unit": 6,
            "Micro Circuit": 5,
            "Interface Circuit": 8,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Medium Projectile Locus Coordinator II": {
        "materials": {
            "Datacore - Nuclear Physics": 2 / INVENTION_RATE,
            "Datacore - Mechanical Engineering": 2 / INVENTION_RATE,
            "Trigger Unit": 3,
            "Micro Circuit": 5,
            "Interface Circuit": 6,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Medium Projectile Metastasis Adjuster II": {
        "materials": {
            "Datacore - Nuclear Physics": 2 / INVENTION_RATE,
            "Datacore - Mechanical Engineering": 2 / INVENTION_RATE,
            "Trigger Unit": 3,
            "Micro Circuit": 5,
            "Interface Circuit": 6,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    # Resource Processing Rigs
    "Medium Salvage Tackle II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 2 / INVENTION_RATE,
            "Datacore - Nanite Engineering": 2 / INVENTION_RATE,
            "Nanite Compound": 3,
            "Interface Circuit": 5,
            "Intact Armor Plates": 5,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    # Scanning Rigs
    "Medium Emission Scope Sharpener II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 2 / INVENTION_RATE,
            "Datacore - Electronic Engineering": 2 / INVENTION_RATE,
            "Artificial Neural Network": 5,
            "Power Circuit": 6,
            "Conductive Thermoplastic": 3,
            "R.A.M.- Electronics": 1,
        }
    },
    "Medium Gravity Capacitor Upgrade II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 2 / INVENTION_RATE,
            "Datacore - Electronic Engineering": 2 / INVENTION_RATE,
            "Artificial Neural Network": 3,
            "Power Circuit": 5,
            "Conductive Thermoplastic": 6,
            "R.A.M.- Electronics": 1,
        }
    },
    "Medium Memetic Algorithm Bank II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 2 / INVENTION_RATE,
            "Datacore - Electronic Engineering": 2 / INVENTION_RATE,
            "Artificial Neural Network": 5,
            "Power Circuit": 6,
            "Conductive Thermoplastic": 3,
            "R.A.M.- Electronics": 1,
        }
    },
    "Medium Signal Focusing Kit II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 2 / INVENTION_RATE,
            "Datacore - Electronic Engineering": 2 / INVENTION_RATE,
            "Artificial Neural Network": 5,
            "Micro Circuit": 3,
            "Logic Circuit": 3,
            "R.A.M.- Electronics": 1,
            "Miniature Electronics": 12,
        }
    },
    # Shield Rigs
    "Medium Core Defense Capacitor Safeguard II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 2 / INVENTION_RATE,
            "Datacore - Quantum Physics": 2 / INVENTION_RATE,
            "Intact Shield Emitter": 1,
            "Micro Circuit": 3,
            "Interface Circuit": 3,
            "R.A.M.- Shield Tech": 1,
        }
    },
    "Medium Core Defense Charge Economizer II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 2 / INVENTION_RATE,
            "Datacore - Quantum Physics": 2 / INVENTION_RATE,
            "Intact Shield Emitter": 1,
            "Micro Circuit": 5,
            "Interface Circuit": 5,
            "R.A.M.- Shield Tech": 1,
        }
    },
    "Medium Core Defense Field Extender II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 2 / INVENTION_RATE,
            "Datacore - Quantum Physics": 2 / INVENTION_RATE,
            "Power Circuit": 6,
            "Logic Circuit": 6,
            "Enhanced Ward Console": 3,
            "R.A.M.- Shield Tech": 1,
        }
    },
    "Medium Core Defense Field Purger II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 2 / INVENTION_RATE,
            "Datacore - Quantum Physics": 2 / INVENTION_RATE,
            "Power Circuit": 6,
            "Logic Circuit": 6,
            "Enhanced Ward Console": 3,
            "R.A.M.- Shield Tech": 1,
        }
    },
    "Medium Core Defense Operational Solidifier II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 2 / INVENTION_RATE,
            "Datacore - Quantum Physics": 2 / INVENTION_RATE,
            "Power Circuit": 6,
            "Logic Circuit": 6,
            "Enhanced Ward Console": 3,
            "R.A.M.- Shield Tech": 1,
        }
    },
    "Medium EM Shield Reinforcer II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 2 / INVENTION_RATE,
            "Datacore - Quantum Physics": 2 / INVENTION_RATE,
            "Intact Shield Emitter": 3,
            "Micro Circuit": 5,
            "Interface Circuit": 5,
            "R.A.M.- Shield Tech": 1,
        }
    },
    "Medium Explosive Shield Reinforcer II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 2 / INVENTION_RATE,
            "Datacore - Quantum Physics": 2 / INVENTION_RATE,
            "Intact Shield Emitter": 3,
            "Micro Circuit": 5,
            "Interface Circuit": 5,
            "R.A.M.- Shield Tech": 1,
        }
    },
    "Medium Kinetic Shield Reinforcer II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 2 / INVENTION_RATE,
            "Datacore - Quantum Physics": 2 / INVENTION_RATE,
            "Intact Shield Emitter": 3,
            "Micro Circuit": 5,
            "Interface Circuit": 5,
            "R.A.M.- Shield Tech": 1,
        }
    },
    "Medium Thermal Shield Reinforcer II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 2 / INVENTION_RATE,
            "Datacore - Quantum Physics": 2 / INVENTION_RATE,
            "Intact Shield Emitter": 3,
            "Micro Circuit": 5,
            "Interface Circuit": 5,
            "R.A.M.- Shield Tech": 1,
        }
    },
    # Targeting Rigs
    "Medium Ionic Field Projector II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 2 / INVENTION_RATE,
            "Datacore - Electronic Engineering": 2 / INVENTION_RATE,
            "Artificial Neural Network": 5,
            "Micro Circuit": 6,
            "Logic Circuit": 6,
            "R.A.M.- Electronics": 1,
            "Miniature Electronics": 12,
        }
    },
    "Medium Targeting System Subcontroller II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 2 / INVENTION_RATE,
            "Datacore - Electronic Engineering": 2 / INVENTION_RATE,
            "Artificial Neural Network": 5,
            "Micro Circuit": 6,
            "Logic Circuit": 6,
            "R.A.M.- Electronics": 1,
            "Miniature Electronics": 12,
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
    header_component = "Medium Rig"
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
