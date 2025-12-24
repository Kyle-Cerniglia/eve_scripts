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
            "Particle Accelerator Unit": 12,
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
    # Electronics and Sensor Upgrades
    "Auto Targeting System II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 1 / 0.47 / 10,
            "Datacore - Electronic Engineering": 1 / 0.47 / 10,
            "Auto Targeting System I": 1,
            "Morphite": 3,
            "Ladar Sensor Cluster": 3,
            "Quantum Microprocessor": 1,
            "Electrolytic Capacitor Unit": 1,
            "Transmitter": 5,
            "Miniature Electronics": 11,
            "R.A.M.- Electronics": 1,
        }
    },
    "Improved Cloaking Device II": {
        "materials": {
            "Datacore - Quantum Physics": 2 / 0.459 / 10,
            "Datacore - Graviton Physics": 2 / 0.459 / 10,
            "Prototype Cloaking Device I": 1,
            "Photon Microprocessor": 15,
            "Graviton Pulse Generator": 15,
            "R.A.M.- Electronics": 1,
        }
    },
    "Covert Ops Cloaking Device II": {
        "materials": {
            "Datacore - Quantum Physics": 2 / 0.459 / 10,
            "Datacore - Graviton Physics": 2 / 0.459 / 10,
            "Prototype Cloaking Device I": 1,
            "Photon Microprocessor": 33,
            "Graviton Pulse Generator": 26,
            "Transmitter": 22,
            "Miniature Electronics": 22,
            "R.A.M.- Electronics": 1,
        }
    },
    "Co-Processor II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 2 / 0.47 / 10,
            "Datacore - Electronic Engineering": 2 / 0.47 / 10,
            "Co-Processor I": 1,
            "Morphite": 1,
            "Photon Microprocessor": 5,
            "Oscillator Capacitor Unit": 3,
            "Miniature Electronics": 24,
            "R.A.M.- Electronics": 1,
        }
    },
    "Passive Targeter II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 1 / 0.47 / 10,
            "Datacore - Electronic Engineering": 1 / 0.47 / 10,
            "Passive Targeter I": 1,
            "Morphite": 1,
            "Ladar Sensor Cluster": 1,
            "Nanomechanical Microprocessor": 5,
            "Transmitter": 8,
            "Miniature Electronics": 6,
            "R.A.M.- Electronics": 1,
        }
    },
    "Remote Sensor Booster II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 1 / 0.47 / 10,
            "Datacore - Electronic Engineering": 1 / 0.47 / 10,
            "Remote Sensor Booster I": 1,
            "Morphite": 6,
            "Gravimetric Sensor Cluster": 8,
            "Quantum Microprocessor": 5,
            "Transmitter": 8,
            "Miniature Electronics": 9,
            "R.A.M.- Electronics": 1,
        }
    },
    "Sensor Booster II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 2 / 0.47 / 10,
            "Datacore - Electronic Engineering": 2 / 0.47 / 10,
            "Sensor Booster I": 1,
            "Morphite": 3,
            "Gravimetric Sensor Cluster": 6,
            "Quantum Microprocessor": 5,
            "Transmitter": 5,
            "Miniature Electronics": 11,
            "R.A.M.- Electronics": 1,
        }
    },
    "Signal Amplifier II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 2 / 0.47 / 10,
            "Datacore - Electronic Engineering": 2 / 0.47 / 10,
            "Signal Amplifier I": 1,
            "Morphite": 1,
            "Gravimetric Sensor Cluster": 8,
            "Quantum Microprocessor": 5,
            "Transmitter": 3,
            "Miniature Electronics": 8,
            "R.A.M.- Electronics": 1,
        }
    },
    "Small Tractor Beam II": {
        "materials": {
            "Datacore - Laser Physics": 1 / 0.448 / 10,
            "Datacore - Mechanical Engineering": 1 / 0.448 / 10,
            "Small Tractor Beam I": 1,
            "Morphite": 1,
            "Laser Focusing Crystals": 12,
            "Transmitter": 12,
            "R.A.M.- Energy Tech": 1,
        }
    },
    # Engineering Equipment
    "Micro Auxiliary Power Core II": {
        "materials": {
            "Datacore - High Energy Physics": 1 / 0.459 / 10,
            "Datacore - Quantum Physics": 1 / 0.459 / 10,
            "Micro Auxiliary Power Core I": 1,
            "Morphite": 1,
            "Nanoelectrical Microprocessor": 6,
            "Superconductors": 6,
            "R.A.M.- Energy Tech": 1,
        }
    },
    "Large Cap Battery II": {
        "materials": {
            "Datacore - High Energy Physics": 3 / 0.459 / 10,
            "Datacore - Quantum Physics": 3 / 0.459 / 10,
            "Large Cap Battery I": 1,
            "Morphite": 6,
            "Nanoelectrical Microprocessor": 6,
            "Tesseract Capacitor Unit": 12,
            "Superconductors": 6,
            "R.A.M.- Energy Tech": 1,
        }
    },
    "Medium Cap Battery II": {
        "materials": {
            "Datacore - High Energy Physics": 2 / 0.459 / 10,
            "Datacore - Quantum Physics": 2 / 0.459 / 10,
            "Medium Cap Battery I": 1,
            "Morphite": 5,
            "Nanoelectrical Microprocessor": 5,
            "Tesseract Capacitor Unit": 6,
            "Superconductors": 5,
            "R.A.M.- Energy Tech": 1,
        }
    },
    "Small Cap Battery II": {
        "materials": {
            "Datacore - High Energy Physics": 1 / 0.459 / 10,
            "Datacore - Quantum Physics": 1 / 0.459 / 10,
            "Small Cap Battery I": 1,
            "Morphite": 3,
            "Nanoelectrical Microprocessor": 3,
            "Tesseract Capacitor Unit": 3,
            "Superconductors": 3,
            "R.A.M.- Energy Tech": 1,
        }
    },
    "Heavy Capacitor Booster II": {
        "materials": {
            "Datacore - High Energy Physics": 3 / 0.459 / 10,
            "Datacore - Quantum Physics": 3 / 0.459 / 10,
            "Heavy Capacitor Booster I": 1,
            "Morphite": 6,
            "Nanoelectrical Microprocessor": 6,
            "Tesseract Capacitor Unit": 12,
            "Superconductors": 24,
            "R.A.M.- Energy Tech": 1,
        }
    },
    "Medium Capacitor Booster II": {
        "materials": {
            "Datacore - High Energy Physics": 2 / 0.459 / 10,
            "Datacore - Quantum Physics": 2 / 0.459 / 10,
            "Medium Capacitor Booster I": 1,
            "Morphite": 3,
            "Nanoelectrical Microprocessor": 5,
            "Tesseract Capacitor Unit": 6,
            "Superconductors": 12,
            "R.A.M.- Energy Tech": 1,
        }
    },
    "Small Capacitor Booster II": {
        "materials": {
            "Datacore - High Energy Physics": 1 / 0.459 / 10,
            "Datacore - Quantum Physics": 1 / 0.459 / 10,
            "Small Capacitor Booster I": 1,
            "Morphite": 3,
            "Nanoelectrical Microprocessor": 3,
            "Tesseract Capacitor Unit": 3,
            "Superconductors": 6,
            "R.A.M.- Energy Tech": 1,
        }
    },
    "Capacitor Flux Coil II": {
        "materials": {
            "Datacore - High Energy Physics": 1 / 0.459 / 10,
            "Datacore - Quantum Physics": 1 / 0.459 / 10,
            "Capacitor Flux Coil I": 1,
            "Morphite": 1,
            "Nanoelectrical Microprocessor": 1,
            "Tesseract Capacitor Unit": 5,
            "Superconductors": 5,
            "R.A.M.- Energy Tech": 1,
        }
    },
    "Capacitor Power Relay II": {
        "materials": {
            "Datacore - High Energy Physics": 2 / 0.459 / 10,
            "Datacore - Quantum Physics": 2 / 0.459 / 10,
            "Capacitor Power Relay I": 1,
            "Morphite": 1,
            "Nanoelectrical Microprocessor": 1,
            "Tesseract Capacitor Unit": 1,
            "Superconductors": 8,
            "R.A.M.- Energy Tech": 1,
        }
    },
    "Cap Recharger II": {
        "materials": {
            "Datacore - High Energy Physics": 2 / 0.459 / 10,
            "Datacore - Quantum Physics": 2 / 0.459 / 10,
            "Cap Recharger I": 1,
            "Morphite": 3,
            "Nanoelectrical Microprocessor": 1,
            "Tesseract Capacitor Unit": 1,
            "Superconductors": 5,
            "R.A.M.- Energy Tech": 1,
        }
    },
    "Heavy Energy Neutralizer II": {
        "materials": {
            "Datacore - High Energy Physics": 3 / 0.459 / 10,
            "Datacore - Quantum Physics": 3 / 0.459 / 10,
            "Heavy Energy Neutralizer I": 1,
            "Nanoelectrical Microprocessor": 23,
            "Tesseract Capacitor Unit": 45,
            "Superconductors": 30,
            "R.A.M.- Energy Tech": 1,
        }
    },
    "Medium Energy Neutralizer II": {
        "materials": {
            "Datacore - High Energy Physics": 2 / 0.459 / 10,
            "Datacore - Quantum Physics": 2 / 0.459 / 10,
            "Medium Energy Neutralizer I": 1,
            "Nanoelectrical Microprocessor": 15,
            "Tesseract Capacitor Unit": 30,
            "Superconductors": 23,
            "R.A.M.- Energy Tech": 1,
        }
    },
    "Small Energy Neutralizer II": {
        "materials": {
            "Datacore - High Energy Physics": 1 / 0.459 / 10,
            "Datacore - Quantum Physics": 1 / 0.459 / 10,
            "Small Energy Neutralizer I": 1,
            "Nanoelectrical Microprocessor": 8,
            "Tesseract Capacitor Unit": 15,
            "Superconductors": 8,
            "R.A.M.- Energy Tech": 1,
        }
    },
    "Heavy Energy Nosferatu II": {
        "materials": {
            "Datacore - High Energy Physics": 3 / 0.459 / 10,
            "Datacore - Quantum Physics": 3 / 0.459 / 10,
            "Heavy Energy Nosferatu I": 1,
            "Morphite": 24,
            "Nanoelectrical Microprocessor": 30,
            "Tesseract Capacitor Unit": 52,
            "Superconductors": 45,
            "R.A.M.- Energy Tech": 1,
        }
    },
    "Medium Energy Nosferatu II": {
        "materials": {
            "Datacore - High Energy Physics": 2 / 0.459 / 10,
            "Datacore - Quantum Physics": 2 / 0.459 / 10,
            "Medium Energy Nosferatu I": 1,
            "Morphite": 12,
            "Nanoelectrical Microprocessor": 15,
            "Tesseract Capacitor Unit": 30,
            "Superconductors": 30,
            "R.A.M.- Energy Tech": 1,
        }
    },
    "Small Energy Nosferatu II": {
        "materials": {
            "Datacore - High Energy Physics": 2 / 0.459 / 10,
            "Datacore - Quantum Physics": 2 / 0.459 / 10,
            "Small Energy Nosferatu I": 1,
            "Morphite": 6,
            "Nanoelectrical Microprocessor": 8,
            "Tesseract Capacitor Unit": 15,
            "Superconductors": 8,
            "R.A.M.- Energy Tech": 1,
        }
    },
    "Power Diagnostic System II": {
        "materials": {
            "Datacore - High Energy Physics": 2 / 0.459 / 10,
            "Datacore - Quantum Physics": 2 / 0.459 / 10,
            "Power Diagnostic System I": 1,
            "Morphite": 1,
            "Nanoelectrical Microprocessor": 8,
            "Tesseract Capacitor Unit": 1,
            "Superconductors": 1,
            "R.A.M.- Energy Tech": 1,
        }
    },
    "Reactor Control Unit II": {
        "materials": {
            "Datacore - High Energy Physics": 2 / 0.459 / 10,
            "Datacore - Quantum Physics": 2 / 0.459 / 10,
            "Reactor Control Unit I": 1,
            "Morphite": 1,
            "Nanoelectrical Microprocessor": 5,
            "Tesseract Capacitor Unit": 3,
            "Superconductors": 3,
            "R.A.M.- Energy Tech": 1,
        }
    },
    "Large Remote Capacitor Transmitter II": {
        "materials": {
            "Datacore - High Energy Physics": 3 / 0.459 / 10,
            "Datacore - Quantum Physics": 3 / 0.459 / 10,
            "Large Remote Capacitor Transmitter I": 1,
            "Morphite": 14,
            "Nanoelectrical Microprocessor": 14,
            "Tesseract Capacitor Unit": 23,
            "Superconductors": 45,
            "R.A.M.- Energy Tech": 1,
        }
    },
    "Medium Remote Capacitor Transmitter II": {
        "materials": {
            "Datacore - High Energy Physics": 2 / 0.459 / 10,
            "Datacore - Quantum Physics": 2 / 0.459 / 10,
            "Medium Remote Capacitor Transmitter I": 1,
            "Morphite": 9,
            "Nanoelectrical Microprocessor": 9,
            "Tesseract Capacitor Unit": 15,
            "Superconductors": 23,
            "R.A.M.- Energy Tech": 1,
        }
    },
    "Small Remote Capacitor Transmitter II": {
        "materials": {
            "Datacore - High Energy Physics": 1 / 0.459 / 10,
            "Datacore - Quantum Physics": 1 / 0.459 / 10,
            "Small Remote Capacitor Transmitter I": 1,
            "Morphite": 5,
            "Nanoelectrical Microprocessor": 5,
            "Tesseract Capacitor Unit": 8,
            "Superconductors": 15,
            "R.A.M.- Energy Tech": 1,
        }
    },
    # Fleet Assistance Modules
    "Armor Command Burst II": {
        "materials": {
            "Datacore - Molecular Engineering": 2 / 0.434 / 10,
            "Datacore - Nuclear Physics": 2 / 0.434 / 10,
            "Armor Command Burst I": 1,
            "Morphite": 5,
            "Nanoelectrical Microprocessor": 8,
            "Photon Microprocessor": 4,
            "Nanotransistors": 33,
            "Hypersynaptic Fibers": 17,
            "Transmitter": 12,
            "R.A.M.- Electronics": 1,
        }
    },
    "Expedition Command Burst II": {
        "materials": {
            "Datacore - Molecular Engineering": 2 / 0.434 / 10,
            "Datacore - Nuclear Physics": 2 / 0.434 / 10,
            "Expedition Command Burst I": 1,
            "Morphite": 5,
            "Nanoelectrical Microprocessor": 8,
            "Photon Microprocessor": 4,
            "Nanotransistors": 33,
            "Hypersynaptic Fibers": 17,
            "Transmitter": 12,
            "R.A.M.- Electronics": 1,
        }
    },
    "Information Command Burst II": {
        "materials": {
            "Datacore - Molecular Engineering": 2 / 0.425 / 10,
            "Datacore - Nuclear Physics": 2 / 0.425 / 10,
            "Information Command Burst I": 1,
            "Morphite": 5,
            "Nanoelectrical Microprocessor": 4,
            "Quantum Microprocessor": 8,
            "Nanotransistors": 33,
            "Hypersynaptic Fibers": 17,
            "Transmitter": 12,
            "R.A.M.- Electronics": 1,
        }
    },
    "Mining Foreman Burst II": {
        "materials": {
            "Datacore - Molecular Engineering": 2 / 0.434 / 10,
            "Datacore - Nuclear Physics": 2 / 0.434 / 10,
            "Mining Foreman Burst I": 1,
            "Morphite": 5,
            "Nanoelectrical Microprocessor": 4,
            "Photon Microprocessor": 8,
            "Nanotransistors": 33,
            "Hypersynaptic Fibers": 17,
            "Transmitter": 12,
            "R.A.M.- Electronics": 1,
        }
    },
    "Shield Command Burst II": {
        "materials": {
            "Datacore - Molecular Engineering": 2 / 0.425 / 10,
            "Datacore - Nuclear Physics": 2 / 0.425 / 10,
            "Shield Command Burst I": 1,
            "Morphite": 5,
            "Nanomechanical Microprocessor": 6,
            "Quantum Microprocessor": 6,
            "Nanotransistors": 33,
            "Hypersynaptic Fibers": 17,
            "Transmitter": 12,
            "R.A.M.- Electronics": 1,
        }
    },
    "Skirmish Command Burst II": {
        "materials": {
            "Datacore - Molecular Engineering": 2 / 0.425 / 10,
            "Datacore - Nuclear Physics": 2 / 0.425 / 10,
            "Skirmish Command Burst I": 1,
            "Morphite": 5,
            "Nanomechanical Microprocessor": 10,
            "Photon Microprocessor": 2,
            "Nanotransistors": 33,
            "Hypersynaptic Fibers": 17,
            "Transmitter": 12,
            "R.A.M.- Electronics": 1,
        }
    },
    # Harvest Equipment
    "Gas Cloud Harvester II": {
        "materials": {
            "Datacore - Laser Physics": 2 / 0.456 / 10,
            "Datacore - Mechanical Engineering": 2 / 0.456 / 10,
            "Gas Cloud Harvester I": 1,
            "Morphite": 15,
            "Photon Microprocessor": 23,
            "Mechanical Parts": 30,
            "Electronic Parts": 30,
            "R.A.M.- Energy Tech": 1,
        }
    },
    "Gas Cloud Scoop II": {
        "materials": {
            "Datacore - Laser Physics": 2 / 0.479 / 10,
            "Datacore - Electromagnetic Physics": 2 / 0.479 / 10,
            "Gas Cloud Scoop I": 1,
            "Photon Microprocessor": 18,
            "Laser Focusing Crystals": 18,
            "Mechanical Parts": 23,
            "R.A.M.- Energy Tech": 1,
        }
    },
    "Ice Harvester II": {
        "materials": {
            "Datacore - Laser Physics": 2 / 0.456 / 10,
            "Datacore - Electromagnetic Physics": 2 / 0.456 / 10,
            "Ice Harvester I": 1,
            "Morphite": 15,
            "Photon Microprocessor": 23,
            "Mechanical Parts": 30,
            "Electronic Parts": 30,
            "R.A.M.- Energy Tech": 1,
        }
    },
    "Ice Mining Laser II": {
        "materials": {
            "Datacore - Laser Physics": 2 / 0.456 / 10,
            "Datacore - Mechanical Engineering": 2 / 0.456 / 10,
            "Ice Mining Laser I": 1,
            "Morphite": 15,
            "Photon Microprocessor": 4,
            "Laser Focusing Crystals": 5,
            "Mechanical Parts": 8,
            "R.A.M.- Energy Tech": 1,
        }
    },
    "Modulated Deep Core Miner II": {
        "materials": {
            "Datacore - Laser Physics": 2 / 0.456 / 10,
            "Datacore - Mechanical Engineering": 2 / 0.456 / 10,
            "Deep Core Mining Laser I": 1,
            "Morphite": 23,
            "Photon Microprocessor": 5,
            "Laser Focusing Crystals": 3,
            "R.A.M.- Energy Tech": 1,
        }
    },
    "Miner II": {
        "materials": {
            "Datacore - Laser Physics": 2 / 0.456 / 10,
            "Datacore - Mechanical Engineering": 2 / 0.456 / 10,
            "Miner I": 1,
            "Morphite": 1,
            "Photon Microprocessor": 5,
            "Laser Focusing Crystals": 3,
            "Mechanical Parts": 8,
            "R.A.M.- Energy Tech": 1,
        }
    },
    "Ice Harvester Upgrade II": {
        "materials": {
            "Datacore - Laser Physics": 2 / 0.456 / 10,
            "Datacore - Mechanical Engineering": 2 / 0.456 / 10,
            "Ice Harvester Upgrade I": 1,
            "Morphite": 5,
            "Laser Focusing Crystals": 8,
            "Mechanical Parts": 8,
            "Miniature Electronics": 3,
            "R.A.M.- Electronics": 1,
        }
    },
    "Mining Laser Upgrade II": {
        "materials": {
            "Datacore - Laser Physics": 2 / 0.456 / 10,
            "Datacore - Mechanical Engineering": 2 / 0.456 / 10,
            "Mining Laser Upgrade I": 1,
            "Morphite": 5,
            "Laser Focusing Crystals": 8,
            "Mechanical Parts": 8,
            "Miniature Electronics": 3,
            "R.A.M.- Electronics": 1,
        }
    },
    "Salvager II": {
        "materials": {
            "Datacore - Laser Physics": 2 / 0.448 / 10,
            "Datacore - Mechanical Engineering": 2 / 0.448 / 10,
            "Salvager I": 1,
            "Ladar Sensor Cluster": 5,
            "Nanomechanical Microprocessor": 5,
            "Transmitter": 12,
            "Miniature Electronics": 9,
            "R.A.M.- Electronics": 1,
        }
    },
    "Modulated Deep Core Strip Miner II": {
        "materials": {
            "Datacore - Laser Physics": 2 / 0.456 / 10,
            "Datacore - Mechanical Engineering": 2 / 0.456 / 10,
            "Strip Miner I": 1,
            "Deep Core Mining Laser I": 1,
            "Morphite": 23,
            "Photon Microprocessor": 5,
            "Laser Focusing Crystals": 3,
            "Mechanical Parts": 6,
            "Electronic Parts": 5,
            "R.A.M.- Energy Tech": 1,
        }
    },
    "Modulated Strip Miner II": {
        "materials": {
            "Datacore - Laser Physics": 2 / 0.456 / 10,
            "Datacore - Mechanical Engineering": 2 / 0.456 / 10,
            "Strip Miner I": 1,
            "Deep Core Mining Laser I": 1,
            "Morphite": 23,
            "Photon Microprocessor": 5,
            "Laser Focusing Crystals": 3,
            "Mechanical Parts": 6,
            "Electronic Parts": 5,
            "R.A.M.- Energy Tech": 1,
        }
    },
    # Hull and armor
    "EM Armor Hardener II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 2 / 0.459 / 10,
            "Datacore - Nanite Engineering": 2 / 0.459 / 10,
            "EM Armor Hardener I": 1,
            "Morphite": 23,
            "Tungsten Carbide Armor Plate": 15,
            "Sustained Shield Emitter": 27,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "Explosive Armor Hardener II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 2 / 0.459 / 10,
            "Datacore - Nanite Engineering": 2 / 0.459 / 10,
            "Explosive Armor Hardener I": 1,
            "Morphite": 23,
            "Fernite Carbide Composite Armor Plate": 15,
            "Sustained Shield Emitter": 27,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "Kinetic Armor Hardener II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 2 / 0.459 / 10,
            "Datacore - Nanite Engineering": 2 / 0.459 / 10,
            "Kinetic Armor Hardener I": 1,
            "Morphite": 23,
            "Titanium Diborite Armor Plate": 15,
            "Sustained Shield Emitter": 27,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "Thermal Armor Hardener II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 2 / 0.459 / 10,
            "Datacore - Nanite Engineering": 2 / 0.459 / 10,
            "Thermal Armor Hardener I": 1,
            "Morphite": 23,
            "Crystalline Carbonide Armor Plate": 15,
            "Sustained Shield Emitter": 27,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "100mm Steel Plates II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 1 / 0.459 / 10,
            "Datacore - Nanite Engineering": 1 / 0.459 / 10,
            "100mm Steel Plates I": 1,
            "Morphite": 3,
            "Tungsten Carbide Armor Plate": 8,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "1600mm Steel Plates II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 3 / 0.459 / 10,
            "Datacore - Nanite Engineering": 3 / 0.459 / 10,
            "1600mm Steel Plates I": 1,
            "Morphite": 48,
            "Tungsten Carbide Armor Plate": 52,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "200mm Steel Plates II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 2 / 0.459 / 10,
            "Datacore - Nanite Engineering": 2 / 0.459 / 10,
            "200mm Steel Plates I": 1,
            "Morphite": 6,
            "Tungsten Carbide Armor Plate": 11,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "400mm Steel Plates II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 2 / 0.459 / 10,
            "Datacore - Nanite Engineering": 2 / 0.459 / 10,
            "400mm Steel Plates I": 1,
            "Morphite": 12,
            "Tungsten Carbide Armor Plate": 17,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "800mm Steel Plates II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 3 / 0.459 / 10,
            "Datacore - Nanite Engineering": 3 / 0.459 / 10,
            "800mm Steel Plates I": 1,
            "Morphite": 24,
            "Tungsten Carbide Armor Plate": 29,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "Large Armor Repairer II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 3 / 0.459 / 10,
            "Datacore - Nanite Engineering": 3 / 0.459 / 10,
            "Large Armor Repairer I": 1,
            "Morphite": 8,
            "Nanoelectrical Microprocessor": 6,
            "Robotics": 12,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "Medium Armor Repairer II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 2 / 0.459 / 10,
            "Datacore - Nanite Engineering": 2 / 0.459 / 10,
            "Medium Armor Repairer I": 1,
            "Morphite": 5,
            "Nanoelectrical Microprocessor": 3,
            "Robotics": 6,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "Small Armor Repairer II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 1 / 0.459 / 10,
            "Datacore - Nanite Engineering": 1 / 0.459 / 10,
            "Small Armor Repairer I": 1,
            "Morphite": 1,
            "Nanoelectrical Microprocessor": 1,
            "Robotics": 3,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "EM Coating II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 1 / 0.459 / 10,
            "Datacore - Nanite Engineering": 1 / 0.459 / 10,
            "EM Coating I": 1,
            "Morphite": 1,
            "Tungsten Carbide Armor Plate": 1,
            "Titanium Diborite Armor Plate": 1,
            "Crystalline Carbonide Armor Plate": 3,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "Explosive Coating II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 1 / 0.459 / 10,
            "Datacore - Nanite Engineering": 1 / 0.459 / 10,
            "Explosive Coating I": 1,
            "Morphite": 1,
            "Fernite Carbide Composite Armor Plate": 3,
            "Tungsten Carbide Armor Plate": 3,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "Kinetic Coating II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 1 / 0.459 / 10,
            "Datacore - Nanite Engineering": 1 / 0.459 / 10,
            "Kinetic Coating I": 1,
            "Morphite": 1,
            "Fernite Carbide Composite Armor Plate": 1,
            "Titanium Diborite Armor Plate": 3,
            "Crystalline Carbonide Armor Plate": 1,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "Multispectrum Coating II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 1 / 0.459 / 10,
            "Datacore - Molecular Engineering": 1 / 0.459 / 10,
            "Multispectrum Coating I": 1,
            "Morphite": 1,
            "Fernite Carbide Composite Armor Plate": 1,
            "Tungsten Carbide Armor Plate": 1,
            "Titanium Diborite Armor Plate": 1,
            "Crystalline Carbonide Armor Plate": 1,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "Thermal Coating II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 1 / 0.459 / 10,
            "Datacore - Nanite Engineering": 1 / 0.459 / 10,
            "Thermal Coating I": 1,
            "Morphite": 1,
            "Fernite Carbide Composite Armor Plate": 3,
            "Crystalline Carbonide Armor Plate": 3,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "Assault Damage Control II": {
        "materials": {
            "Datacore - Molecular Engineering": 2 / 0.445 / 10,
            "Datacore - Nanite Engineering": 2 / 0.445 / 10,
            "Assault Damage Control I": 1,
            "Morphite": 1,
            "Quantum Microprocessor": 1,
            "Fernite Carbide Composite Armor Plate": 1,
            "Oscillator Capacitor Unit": 1,
            "Plasma Pulse Generator": 1,
            "Mechanical Parts": 6,
            "Construction Blocks": 4,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "Damage Control II": {
        "materials": {
            "Datacore - Molecular Engineering": 2 / 0.445 / 10,
            "Datacore - Nanite Engineering": 2 / 0.445 / 10,
            "Damage Control I": 1,
            "Morphite": 1,
            "Quantum Microprocessor": 1,
            "Fernite Carbide Composite Armor Plate": 1,
            "Oscillator Capacitor Unit": 1,
            "Plasma Pulse Generator": 1,
            "Mechanical Parts": 5,
            "Construction Blocks": 3,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "EM Energized Membrane II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 2 / 0.459 / 10,
            "Datacore - Nanite Engineering": 2 / 0.459 / 10,
            "EM Energized Membrane I": 1,
            "Morphite": 5,
            "Tungsten Carbide Armor Plate": 3,
            "Titanium Diborite Armor Plate": 3,
            "Tesseract Capacitor Unit": 3,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "Explosive Energized Membrane II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 2 / 0.459 / 10,
            "Datacore - Nanite Engineering": 2 / 0.459 / 10,
            "Explosive Energized Membrane I": 1,
            "Morphite": 5,
            "Tungsten Carbide Armor Plate": 5,
            "Crystalline Carbonide Armor Plate": 5,
            "Tesseract Capacitor Unit": 3,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "Kinetic Energized Membrane II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 2 / 0.459 / 10,
            "Datacore - Nanite Engineering": 2 / 0.459 / 10,
            "Kinetic Energized Membrane I": 1,
            "Morphite": 5,
            "Fernite Carbide Composite Armor Plate": 3,
            "Titanium Diborite Armor Plate": 3,
            "Crystalline Carbonide Armor Plate": 3,
            "Tesseract Capacitor Unit": 3,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "Multispectrum Energized Membrane II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 2 / 0.459 / 10,
            "Datacore - Nanite Engineering": 2 / 0.459 / 10,
            "Multispectrum Energized Membrane I": 1,
            "Morphite": 15,
            "Fernite Carbide Composite Armor Plate": 3,
            "Tungsten Carbide Armor Plate": 3,
            "Titanium Diborite Armor Plate": 3,
            "Crystalline Carbonide Armor Plate": 3,
            "Tesseract Capacitor Unit": 9,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "Thermal Energized Membrane II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 2 / 0.459 / 10,
            "Datacore - Nanite Engineering": 2 / 0.459 / 10,
            "Thermal Energized Membrane I": 1,
            "Morphite": 5,
            "Crystalline Carbonide Armor Plate": 6,
            "Tesseract Capacitor Unit": 3,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "Large Hull Repairer II": {
        "materials": {
            "Datacore - Molecular Engineering": 3 / 0.445 / 10,
            "Datacore - Nanite Engineering": 3 / 0.445 / 10,
            "Large Hull Repairer I": 1,
            "Morphite": 8,
            "Nanomechanical Microprocessor": 6,
            "Robotics": 12,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "Medium Hull Repairer II": {
        "materials": {
            "Datacore - Molecular Engineering": 2 / 0.445 / 10,
            "Datacore - Nanite Engineering": 2 / 0.445 / 10,
            "Medium Hull Repairer I": 1,
            "Morphite": 5,
            "Nanomechanical Microprocessor": 3,
            "Robotics": 6,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "Small Hull Repairer II": {
        "materials": {
            "Datacore - Molecular Engineering": 1 / 0.445 / 10,
            "Datacore - Nanite Engineering": 1 / 0.445 / 10,
            "Small Hull Repairer I": 1,
            "Morphite": 1,
            "Nanomechanical Microprocessor": 1,
            "Robotics": 3,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "Expanded Cargohold II": {
        "materials": {
            "Datacore - Molecular Engineering": 2 / 0.445 / 10,
            "Datacore - Nanite Engineering": 2 / 0.445 / 10,
            "Expanded Cargohold I": 1,
            "Morphite": 1,
            "Nanomechanical Microprocessor": 1,
            "Crystalline Carbonide Armor Plate": 1,
            "Construction Blocks": 8,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "Nanofiber Internal Structure II": {
        "materials": {
            "Datacore - Molecular Engineering": 1 / 0.445 / 10,
            "Datacore - Nanite Engineering": 1 / 0.445 / 10,
            "Nanofiber Internal Structure I": 1,
            "Morphite": 1,
            "Construction Blocks": 8,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "Reinforced Bulkheads II": {
        "materials": {
            "Datacore - Molecular Engineering": 1 / 0.445 / 10,
            "Datacore - Nanite Engineering": 1 / 0.445 / 10,
            "Reinforced Bulkheads I": 1,
            "Morphite": 1,
            "Construction Blocks": 8,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "Layered Coating II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 1 / 0.459 / 10,
            "Datacore - Nanite Engineering": 1 / 0.459 / 10,
            "Layered Coating I": 1,
            "Morphite": 1,
            "Tungsten Carbide Armor Plate": 3,
            "Titanium Diborite Armor Plate": 3,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "Layered Energized Membrane II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 2 / 0.459 / 10,
            "Datacore - Nanite Engineering": 2 / 0.459 / 10,
            "Layered Energized Membrane I": 1,
            "Morphite": 5,
            "Fernite Carbide Composite Armor Plate": 1,
            "Tungsten Carbide Armor Plate": 3,
            "Titanium Diborite Armor Plate": 3,
            "Tesseract Capacitor Unit": 3,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "Heavy Mutadaptive Remote Armor Repairer II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 2 / 0.442 / 10,
            "Datacore - Nanite Engineering": 2 / 0.442 / 10,
            "Heavy Mutadaptive Remote Armor Repairer I": 1,
            "Morphite": 5,
            "Nanoelectrical Microprocessor": 3,
            "Robotics": 12,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "Large Remote Armor Repairer II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 3 / 0.459 / 10,
            "Datacore - Nanite Engineering": 3 / 0.459 / 10,
            "Large Remote Armor Repairer I": 1,
            "Morphite": 8,
            "Nanoelectrical Microprocessor": 6,
            "Robotics": 12,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "Medium Remote Armor Repairer II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 2 / 0.459 / 10,
            "Datacore - Nanite Engineering": 2 / 0.459 / 10,
            "Medium Remote Armor Repairer I": 1,
            "Morphite": 5,
            "Nanoelectrical Microprocessor": 3,
            "Robotics": 12,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "Small Remote Armor Repairer II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 1 / 0.459 / 10,
            "Datacore - Nanite Engineering": 1 / 0.459 / 10,
            "Small Remote Armor Repairer I": 1,
            "Morphite": 1,
            "Nanoelectrical Microprocessor": 1,
            "Robotics": 12,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "Large Remote Hull Repairer II": {
        "materials": {
            "Datacore - Molecular Engineering": 3 / 0.445 / 10,
            "Datacore - Nanite Engineering": 3 / 0.445 / 10,
            "Large Remote Hull Repairer I": 1,
            "Morphite": 9,
            "Nanomechanical Microprocessor": 26,
            "Robotics": 26,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "Medium Remote Hull Repairer II": {
        "materials": {
            "Datacore - Molecular Engineering": 2 / 0.445 / 10,
            "Datacore - Nanite Engineering": 2 / 0.445 / 10,
            "Medium Remote Hull Repairer I": 1,
            "Morphite": 5,
            "Nanomechanical Microprocessor": 12,
            "Robotics": 12,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "Small Remote Hull Repairer II": {
        "materials": {
            "Datacore - Molecular Engineering": 2 / 0.445 / 10,
            "Datacore - Nanite Engineering": 2 / 0.445 / 10,
            "Small Remote Hull Repairer I": 1,
            "Morphite": 1,
            "Nanomechanical Microprocessor": 6,
            "Robotics": 6,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    # Propulsion
    "100MN Afterburner II": {
        "materials": {
            "Datacore - Molecular Engineering": 3 / 0.425 / 10,
            "Datacore - Rocket Science": 3 / 0.425 / 10,
            "100MN Afterburner I": 1,
            "Morphite": 12,
            "Plasma Thruster": 12,
            "Ion Thruster": 15,
            "Antimatter Reactor Unit": 8,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "10MN Afterburner II": {
        "materials": {
            "Datacore - Molecular Engineering": 2 / 0.425 / 10,
            "Datacore - Rocket Science": 2 / 0.425 / 10,
            "10MN Afterburner I": 1,
            "Morphite": 6,
            "Plasma Thruster": 6,
            "Ion Thruster": 15,
            "Antimatter Reactor Unit": 8,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "1MN Afterburner II": {
        "materials": {
            "Datacore - Molecular Engineering": 1 / 0.425 / 10,
            "Datacore - Rocket Science": 1 / 0.425 / 10,
            "1MN Afterburner I": 1,
            "Morphite": 1,
            "Plasma Thruster": 3,
            "Ion Thruster": 15,
            "Antimatter Reactor Unit": 8,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "500MN Microwarpdrive II": {
        "materials": {
            "Datacore - Molecular Engineering": 3 / 0.425 / 10,
            "Datacore - Rocket Science": 3 / 0.425 / 10,
            "500MN Microwarpdrive I": 1,
            "Morphite": 74,
            "Plasma Thruster": 95,
            "Ion Thruster": 15,
            "Antimatter Reactor Unit": 8,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "50MN Microwarpdrive II": {
        "materials": {
            "Datacore - Molecular Engineering": 2 / 0.425 / 10,
            "Datacore - Rocket Science": 2 / 0.425 / 10,
            "50MN Microwarpdrive I": 1,
            "Morphite": 33,
            "Plasma Thruster": 48,
            "Ion Thruster": 15,
            "Antimatter Reactor Unit": 8,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "5MN Microwarpdrive II": {
        "materials": {
            "Datacore - Molecular Engineering": 1 / 0.425 / 10,
            "Datacore - Nanite Engineering": 1 / 0.425 / 10,
            "5MN Microwarpdrive I": 1,
            "Morphite": 17,
            "Plasma Thruster": 24,
            "Ion Thruster": 15,
            "Antimatter Reactor Unit": 8,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "Inertial Stabilizers II": {
        "materials": {
            "Datacore - Molecular Engineering": 1 / 0.436 / 10,
            "Datacore - Rocket Science": 1 / 0.436 / 10,
            "Inertial Stabilizers I": 1,
            "Morphite": 1,
            "Plasma Thruster": 3,
            "Mechanical Parts": 5,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "Interdiction Nullifier II": {
        "materials": {
            "Datacore - Quantum Physics": 2 / 0.47 / 10,
            "Datacore - Electronic Engineering": 2 / 0.47 / 10,
            "Interdiction Nullifier I": 1,
            "Morphite": 5,
            "Nanomechanical Microprocessor": 6,
            "R.A.M.- Electronics": 2,
        }
    },
    "Overdrive Injector System II": {
        "materials": {
            "Datacore - Quantum Physics": 1 / 0.436 / 10,
            "Datacore - Electronic Engineering": 1 / 0.436 / 10,
            "Overdrive Injector System I": 1,
            "Morphite": 1,
            "Plasma Thruster": 5,
            "Mechanical Parts": 3,
            "R.A.M.- Armor/Hull Tech": 1,
        }
    },
    "Warp Core Stabilizer II": {
        "materials": {
            "Datacore - Quantum Physics": 2 / 0.47 / 10,
            "Datacore - Electronic Engineering": 2 / 0.47 / 10,
            "Warp Core Stabilizer I": 1,
            "Morphite": 5,
            "Nanomechanical Microprocessor": 5,
            "R.A.M.- Electronics": 1,
        }
    },
    # Scanning Equipment
    "Data Analyzer II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 2 / 0.47 / 10,
            "Datacore - Electronic Engineering": 2 / 0.47 / 10,
            "Data Analyzer I": 1,
            "Ladar Sensor Cluster": 5,
            "Quantum Microprocessor": 5,
            "Transmitter": 12,
            "Miniature Electronics": 9,
            "R.A.M.- Electronics": 1,
        }
    },
    "Relic Analyzer II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 2 / 0.47 / 10,
            "Datacore - Electronic Engineering": 2 / 0.47 / 10,
            "Relic Analyzer I": 1,
            "Ladar Sensor Cluster": 5,
            "Nanoelectrical Microprocessor": 5,
            "Transmitter": 12,
            "Miniature Electronics": 9,
            "R.A.M.- Electronics": 1,
        }
    },
    "Cargo Scanner II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 1 / 0.47 / 10,
            "Datacore - Electronic Engineering": 1 / 0.47 / 10,
            "Cargo Scanner I": 1,
            "Nanoelectrical Microprocessor": 5,
            "Transmitter": 3,
            "Miniature Electronics": 5,
            "R.A.M.- Electronics": 1,
        }
    },
    "Entosis Link II": {
        "materials": {
            "Datacore - Electronic Engineering": 3 / 0.442 / 10,
            "Datacore - Graviton Physics": 3 / 0.442 / 10,
            "Entosis Link I": 1,
            "Morphite": 2940,
            "Fusion Reactor Unit": 69,
            "Nuclear Reactor Unit": 69,
            "Antimatter Reactor Unit": 69,
            "Graviton Reactor Unit": 69,
            "Electrolytic Capacitor Unit": 79,
            "Scalar Capacitor Unit": 98,
            "Oscillator Capacitor Unit": 157,
            "Tesseract Capacitor Unit": 79,
            "Synthetic Synapses": 20,
            "Transcranial Microcontrollers": 20,
            "Transmitter": 40,
            "R.A.M.- Electronics": 1,
        }
    },
    "Mining Survey Chipset II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 1 / 0.47 / 10,
            "Datacore - Electronic Engineering": 1 / 0.47 / 10,
            "Mining Survey Chipset I": 1,
            "Morphite": 1,
            "Nanoelectrical Microprocessor": 5,
            "Transmitter": 3,
            "Miniature Electronics": 5,
            "R.A.M.- Electronics": 1,
        }
    },
    "Core Probe Launcher II": {
        "materials": {
            "Datacore - Rocket Science": 1 / 0.425 / 10,
            "Datacore - Nuclear Physics": 1 / 0.425 / 10,
            "Core Probe Launcher I": 1,
            "Morphite": 1,
            "Quantum Microprocessor": 6,
            "Guidance Systems": 6,
            "R.A.M.- Electronics": 1,
        }
    },
    "Expanded Probe Launcher II": {
        "materials": {
            "Datacore - Rocket Science": 1 / 0.425 / 10,
            "Datacore - Nuclear Physics": 1 / 0.425 / 10,
            "Expanded Probe Launcher I": 1,
            "Morphite": 1,
            "Quantum Microprocessor": 6,
            "Guidance Systems": 6,
            "R.A.M.- Electronics": 1,
        }
    },
    "Scan Acquisition Array II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 2 / 0.47 / 10,
            "Datacore - Electronic Engineering": 2 / 0.47 / 10,
            "Scan Acquisition Array I": 1,
            "Quantum Microprocessor": 3,
            "Spatial Attunement Unit": 8,
            "Transmitter": 9,
            "Miniature Electronics": 6,
            "R.A.M.- Electronics": 1,
        }
    },
    "Scan Pinpointing Array II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 2 / 0.47 / 10,
            "Datacore - Electronic Engineering": 2 / 0.47 / 10,
            "Scan Pinpointing Array I": 1,
            "Quantum Microprocessor": 3,
            "Spatial Attunement Unit": 8,
            "Transmitter": 9,
            "Miniature Electronics": 6,
            "R.A.M.- Electronics": 1,
        }
    },
    "Scan Rangefinding Array II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 2 / 0.47 / 10,
            "Datacore - Electronic Engineering": 2 / 0.47 / 10,
            "Scan Rangefinding Array I": 1,
            "Quantum Microprocessor": 3,
            "Spatial Attunement Unit": 8,
            "Transmitter": 9,
            "Miniature Electronics": 6,
            "R.A.M.- Electronics": 1,
        }
    },
    "Ship Scanner II": {
        "materials": {
            "Datacore - Electromagnetic Physics": 2 / 0.47 / 10,
            "Datacore - Electronic Engineering": 2 / 0.47 / 10,
            "Ship Scanner I": 1,
            "Nanoelectrical Microprocessor": 5,
            "Transmitter": 3,
            "Miniature Electronics": 5,
            "R.A.M.- Electronics": 1,
        }
    },
    "Survey Probe Launcher II": {
        "materials": {
            "Datacore - Rocket Science": 1 / 0.448 / 10,
            "Datacore - Mechanical Engineering": 1 / 0.448 / 10,
            "Survey Probe Launcher I": 1,
            "Morphite": 1,
            "Quantum Microprocessor": 6,
            "Guidance Systems": 6,
            "R.A.M.- Electronics": 1,
        }
    },
    # Shield
    "Large Remote Shield Booster II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 3 / 0.47 / 10,
            "Datacore - Quantum Physics": 3 / 0.47 / 10,
            "Large Remote Shield Booster I": 1,
            "Morphite": 5,
            "Linear Shield Emitter": 12,
            "Transmitter": 12,
            "R.A.M.- Shield Tech": 1,
        }
    },
    "Medium Remote Shield Booster II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 2 / 0.47 / 10,
            "Datacore - Quantum Physics": 2 / 0.47 / 10,
            "Medium Remote Shield Booster I": 1,
            "Morphite": 3,
            "Linear Shield Emitter": 6,
            "Transmitter": 6,
            "R.A.M.- Shield Tech": 1,
        }
    },
    "Small Remote Shield Booster II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 1 / 0.47 / 10,
            "Datacore - Quantum Physics": 1 / 0.47 / 10,
            "Small Remote Shield Booster I": 1,
            "Morphite": 1,
            "Linear Shield Emitter": 3,
            "Transmitter": 3,
            "R.A.M.- Shield Tech": 1,
        }
    },
    "Shield Boost Amplifier II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 3 / 0.47 / 10,
            "Datacore - Quantum Physics": 3 / 0.47 / 10,
            "Shield Boost Amplifier I": 1,
            "Morphite": 5,
            "Sustained Shield Emitter": 6,
            "Superconductors": 3,
            "R.A.M.- Shield Tech": 1,
        }
    },
    "X-Large Shield Booster II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 3 / 0.47 / 10,
            "Datacore - Quantum Physics": 3 / 0.47 / 10,
            "X-Large Shield Booster I": 1,
            "Morphite": 9,
            "Sustained Shield Emitter": 29,
            "Superconductors": 12,
            "R.A.M.- Shield Tech": 1,
        }
    },
    "Large Shield Booster II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 3 / 0.47 / 10,
            "Datacore - Quantum Physics": 3 / 0.47 / 10,
            "Large Shield Booster I": 1,
            "Morphite": 6,
            "Sustained Shield Emitter": 14,
            "Superconductors": 6,
            "R.A.M.- Shield Tech": 1,
        }
    },
    "Medium Shield Booster II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 2 / 0.47 / 10,
            "Datacore - Quantum Physics": 2 / 0.47 / 10,
            "Medium Shield Booster I": 1,
            "Morphite": 3,
            "Sustained Shield Emitter": 6,
            "Superconductors": 3,
            "R.A.M.- Shield Tech": 1,
        }
    },
    "Small Shield Booster II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 1 / 0.47 / 10,
            "Datacore - Quantum Physics": 1 / 0.47 / 10,
            "Small Shield Booster I": 1,
            "Morphite": 1,
            "Sustained Shield Emitter": 3,
            "Superconductors": 1,
            "R.A.M.- Shield Tech": 1,
        }
    },
    "Large Shield Extender II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 3 / 0.47 / 10,
            "Datacore - Quantum Physics": 3 / 0.47 / 10,
            "Large Shield Extender I": 1,
            "Morphite": 6,
            "Sustained Shield Emitter": 12,
            "Hydrogen Batteries": 12,
            "R.A.M.- Shield Tech": 1,
        }
    },
    "Medium Shield Extender II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 2 / 0.47 / 10,
            "Datacore - Quantum Physics": 2 / 0.47 / 10,
            "Medium Shield Extender I": 1,
            "Morphite": 5,
            "Sustained Shield Emitter": 6,
            "Hydrogen Batteries": 6,
            "R.A.M.- Shield Tech": 1,
        }
    },
    "Small Shield Extender II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 1 / 0.47 / 10,
            "Datacore - Quantum Physics": 1 / 0.47 / 10,
            "Small Shield Extender I": 1,
            "Morphite": 1,
            "Sustained Shield Emitter": 3,
            "Hydrogen Batteries": 3,
            "R.A.M.- Shield Tech": 1,
        }
    },
    "Shield Flux Coil II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 1 / 0.47 / 10,
            "Datacore - Quantum Physics": 1 / 0.47 / 10,
            "Shield Flux Coil I": 1,
            "Morphite": 1,
            "Nanoelectrical Microprocessor": 1,
            "Tesseract Capacitor Unit": 5,
            "Superconductors": 5,
            "R.A.M.- Energy Tech": 1,
        }
    },
    "EM Shield Hardener II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 2 / 0.47 / 10,
            "Datacore - Quantum Physics": 2 / 0.47 / 10,
            "EM Shield Hardener I": 1,
            "Morphite": 8,
            "Linear Shield Emitter": 24,
            "Superconductors": 9,
            "R.A.M.- Shield Tech": 1,
        }
    },
    "Explosive Shield Hardener II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 2 / 0.47 / 10,
            "Datacore - Quantum Physics": 2 / 0.47 / 10,
            "Explosive Shield Hardener I": 1,
            "Morphite": 8,
            "Deflection Shield Emitter": 24,
            "Superconductors": 9,
            "R.A.M.- Shield Tech": 1,
        }
    },
    "Kinetic Shield Hardener II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 2 / 0.47 / 10,
            "Datacore - Quantum Physics": 2 / 0.47 / 10,
            "Kinetic Shield Hardener I": 1,
            "Morphite": 8,
            "Sustained Shield Emitter": 24,
            "Superconductors": 9,
            "R.A.M.- Shield Tech": 1,
        }
    },
    "Multispectrum Shield Hardener II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 2 / 0.47 / 10,
            "Datacore - Quantum Physics": 2 / 0.47 / 10,
            "Multispectrum Shield Hardener I": 1,
            "Morphite": 11,
            "Deflection Shield Emitter": 8,
            "Pulse Shield Emitter": 8,
            "Linear Shield Emitter": 8,
            "Sustained Shield Emitter": 8,
            "Superconductors": 15,
            "R.A.M.- Shield Tech": 1,
        }
    },
    "Thermal Shield Hardener II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 2 / 0.47 / 10,
            "Datacore - Quantum Physics": 2 / 0.47 / 10,
            "Thermal Shield Hardener I": 1,
            "Morphite": 8,
            "Pulse Shield Emitter": 24,
            "Superconductors": 9,
            "R.A.M.- Shield Tech": 1,
        }
    },
    "Shield Power Relay II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 2 / 0.47 / 10,
            "Datacore - Quantum Physics": 2 / 0.47 / 10,
            "Shield Power Relay I": 1,
            "Morphite": 1,
            "Nanoelectrical Microprocessor": 1,
            "Tesseract Capacitor Unit": 1,
            "Superconductors": 8,
            "R.A.M.- Shield Tech": 1,
        }
    },
    "Shield Recharger II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 2 / 0.47 / 10,
            "Datacore - Quantum Physics": 2 / 0.47 / 10,
            "Shield Recharger I": 1,
            "Morphite": 1,
            "Superconductors": 3,
            "Hydrogen Batteries": 1,
            "R.A.M.- Shield Tech": 1,
        }
    },
    "EM Shield Amplifier II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 1 / 0.47 / 10,
            "Datacore - Quantum Physics": 1 / 0.47 / 10,
            "EM Shield Amplifier I": 1,
            "Morphite": 5,
            "Linear Shield Emitter": 8,
            "Superconductors": 6,
            "R.A.M.- Shield Tech": 1,
        }
    },
    "Explosive Shield Amplifier II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 1 / 0.47 / 10,
            "Datacore - Quantum Physics": 1 / 0.47 / 10,
            "Explosive Shield Amplifier I": 1,
            "Morphite": 5,
            "Deflection Shield Emitter": 8,
            "Superconductors": 6,
            "R.A.M.- Shield Tech": 1,
        }
    },
    "Kinetic Shield Amplifier II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 1 / 0.47 / 10,
            "Datacore - Quantum Physics": 1 / 0.47 / 10,
            "Kinetic Shield Amplifier I": 1,
            "Morphite": 5,
            "Sustained Shield Emitter": 8,
            "Superconductors": 6,
            "R.A.M.- Shield Tech": 1,
        }
    },
    "Thermal Shield Amplifier II": {
        "materials": {
            "Datacore - Hydromagnetic Physics": 1 / 0.47 / 10,
            "Datacore - Quantum Physics": 1 / 0.47 / 10,
            "Thermal Shield Amplifier I": 1,
            "Morphite": 5,
            "Pulse Shield Emitter": 8,
            "Superconductors": 6,
            "R.A.M.- Shield Tech": 1,
        }
    },
    # Smartbombs
    "Large EMP Smartbomb II": {
        "materials": {
            "Datacore - Molecular Engineering": 3 / 0.425 / 10,
            "Datacore - Nuclear Physics": 3 / 0.425 / 10,
            "Large EMP Smartbomb I": 1,
            "Morphite": 12,
            "EM Pulse Generator": 24,
            "R.A.M.- Energy Tech": 1,
        }
    },
    "Large Graviton Smartbomb II": {
        "materials": {
            "Datacore - Molecular Engineering": 3 / 0.425 / 10,
            "Datacore - Nuclear Physics": 3 / 0.425 / 10,
            "Large Graviton Smartbomb I": 1,
            "Morphite": 12,
            "Graviton Pulse Generator": 24,
            "R.A.M.- Energy Tech": 1,
        }
    },
    "Large Plasma Smartbomb II": {
        "materials": {
            "Datacore - Molecular Engineering": 3 / 0.425 / 10,
            "Datacore - Nuclear Physics": 3 / 0.425 / 10,
            "Large Plasma Smartbomb I": 1,
            "Morphite": 12,
            "Plasma Pulse Generator": 24,
            "R.A.M.- Energy Tech": 1,
        }
    },
    "Large Proton Smartbomb II": {
        "materials": {
            "Datacore - Molecular Engineering": 3 / 0.425 / 10,
            "Datacore - Nuclear Physics": 3 / 0.425 / 10,
            "Large Proton Smartbomb I": 1,
            "Morphite": 12,
            "Nuclear Pulse Generator": 24,
            "R.A.M.- Energy Tech": 1,
        }
    },
    "Medium EMP Smartbomb II": {
        "materials": {
            "Datacore - Molecular Engineering": 2 / 0.425 / 10,
            "Datacore - Nuclear Physics": 2 / 0.425 / 10,
            "Medium EMP Smartbomb I": 1,
            "Morphite": 6,
            "EM Pulse Generator": 12,
            "R.A.M.- Energy Tech": 1,
        }
    },
    "Medium Graviton Smartbomb II": {
        "materials": {
            "Datacore - Molecular Engineering": 2 / 0.425 / 10,
            "Datacore - Nuclear Physics": 2 / 0.425 / 10,
            "Medium Graviton Smartbomb I": 1,
            "Morphite": 6,
            "Graviton Pulse Generator": 12,
            "R.A.M.- Energy Tech": 1,
        }
    },
    "Medium Plasma Smartbomb II": {
        "materials": {
            "Datacore - Molecular Engineering": 2 / 0.425 / 10,
            "Datacore - Nuclear Physics": 2 / 0.425 / 10,
            "Medium Plasma Smartbomb I": 1,
            "Morphite": 6,
            "Plasma Pulse Generator": 12,
            "R.A.M.- Energy Tech": 1,
        }
    },
    "Medium Proton Smartbomb II": {
        "materials": {
            "Datacore - Molecular Engineering": 2 / 0.425 / 10,
            "Datacore - Nuclear Physics": 2 / 0.425 / 10,
            "Medium Proton Smartbomb I": 1,
            "Morphite": 6,
            "Nuclear Pulse Generator": 12,
            "R.A.M.- Energy Tech": 1,
        }
    },
    "Small EMP Smartbomb II": {
        "materials": {
            "Datacore - Molecular Engineering": 1 / 0.425 / 10,
            "Datacore - Nuclear Physics": 1 / 0.425 / 10,
            "Small EMP Smartbomb I": 1,
            "Morphite": 3,
            "EM Pulse Generator": 6,
            "R.A.M.- Energy Tech": 1,
        }
    },
    "Small Graviton Smartbomb II": {
        "materials": {
            "Datacore - Molecular Engineering": 1 / 0.425 / 10,
            "Datacore - Nuclear Physics": 1 / 0.425 / 10,
            "Small Graviton Smartbomb I": 1,
            "Morphite": 3,
            "Graviton Pulse Generator": 6,
            "R.A.M.- Energy Tech": 1,
        }
    },
    "Small Plasma Smartbomb II": {
        "materials": {
            "Datacore - Molecular Engineering": 1 / 0.425 / 10,
            "Datacore - Nuclear Physics": 1 / 0.425 / 10,
            "Small Plasma Smartbomb I": 1,
            "Morphite": 3,
            "Plasma Pulse Generator": 6,
            "R.A.M.- Energy Tech": 1,
        }
    },
    "Small Proton Smartbomb II": {
        "materials": {
            "Datacore - Molecular Engineering": 1 / 0.425 / 10,
            "Datacore - Nuclear Physics": 1 / 0.425 / 10,
            "Small Proton Smartbomb I": 1,
            "Morphite": 3,
            "Nuclear Pulse Generator": 6,
            "R.A.M.- Energy Tech": 1,
        }
    },
    # Turrets & Launchers
    "Bomb Launcher II": {
        "materials": {
            "Datacore - Rocket Science": 1 / 0.425 / 10,
            "Datacore - Nuclear Physics": 1 / 0.425 / 10,
            "Bomb Launcher I": 1,
            "Morphite": 1,
            "Quantum Microprocessor": 8,
            "Robotics": 8,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Dual Heavy Beam Laser II": {
        "materials": {
            "Datacore - High Energy Physics": 3 / 0.436 / 10,
            "Datacore - Laser Physics": 3 / 0.436 / 10,
            "Dual Heavy Beam Laser I": 1,
            "Morphite": 33,
            "Laser Focusing Crystals": 32,
            "Robotics": 14,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Mega Beam Laser II": {
        "materials": {
            "Datacore - High Energy Physics": 3 / 0.436 / 10,
            "Datacore - Laser Physics": 3 / 0.436 / 10,
            "Mega Beam Laser I": 1,
            "Morphite": 36,
            "Laser Focusing Crystals": 35,
            "Robotics": 14,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Tachyon Beam Laser II": {
        "materials": {
            "Datacore - High Energy Physics": 3 / 0.436 / 10,
            "Datacore - Laser Physics": 3 / 0.436 / 10,
            "Mega Beam Laser I": 1,
            "Morphite": 38,
            "Laser Focusing Crystals": 36,
            "Robotics": 14,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Focused Medium Beam Laser II": {
        "materials": {
            "Datacore - High Energy Physics": 2 / 0.436 / 10,
            "Datacore - Laser Physics": 2 / 0.436 / 10,
            "Focused Medium Beam Laser I": 1,
            "Morphite": 17,
            "Laser Focusing Crystals": 17,
            "Robotics": 5,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Heavy Beam Laser II": {
        "materials": {
            "Datacore - High Energy Physics": 2 / 0.436 / 10,
            "Datacore - Laser Physics": 2 / 0.436 / 10,
            "Heavy Beam Laser I": 1,
            "Morphite": 20,
            "Laser Focusing Crystals": 20,
            "Robotics": 5,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Quad Light Beam Laser II": {
        "materials": {
            "Datacore - High Energy Physics": 2 / 0.436 / 10,
            "Datacore - Laser Physics": 2 / 0.436 / 10,
            "Quad Light Beam Laser I": 1,
            "Morphite": 14,
            "Laser Focusing Crystals": 14,
            "Robotics": 5,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Dual Light Beam Laser II": {
        "materials": {
            "Datacore - High Energy Physics": 1 / 0.436 / 10,
            "Datacore - Laser Physics": 1 / 0.436 / 10,
            "Dual Light Beam Laser I": 1,
            "Morphite": 5,
            "Laser Focusing Crystals": 8,
            "Robotics": 1,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Small Focused Beam Laser II": {
        "materials": {
            "Datacore - High Energy Physics": 1 / 0.436 / 10,
            "Datacore - Laser Physics": 1 / 0.436 / 10,
            "Small Focused Beam Laser I": 1,
            "Morphite": 8,
            "Laser Focusing Crystals": 11,
            "Robotics": 1,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Dual Heavy Pulse Laser II": {
        "materials": {
            "Datacore - High Energy Physics": 3 / 0.436 / 10,
            "Datacore - Laser Physics": 3 / 0.436 / 10,
            "Dual Heavy Pulse Laser I": 1,
            "Morphite": 32,
            "Laser Focusing Crystals": 30,
            "Robotics": 14,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Mega Pulse Laser II": {
        "materials": {
            "Datacore - High Energy Physics": 3 / 0.436 / 10,
            "Datacore - Laser Physics": 3 / 0.436 / 10,
            "Mega Pulse Laser I": 1,
            "Morphite": 35,
            "Laser Focusing Crystals": 33,
            "Robotics": 14,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Focused Medium Pulse Laser II": {
        "materials": {
            "Datacore - High Energy Physics": 2 / 0.436 / 10,
            "Datacore - Laser Physics": 2 / 0.436 / 10,
            "Focused Medium Pulse Laser I": 1,
            "Morphite": 15,
            "Laser Focusing Crystals": 15,
            "Robotics": 5,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Heavy Pulse Laser II": {
        "materials": {
            "Datacore - High Energy Physics": 2 / 0.436 / 10,
            "Datacore - Laser Physics": 2 / 0.436 / 10,
            "Heavy Pulse Laser I": 1,
            "Morphite": 17,
            "Laser Focusing Crystals": 18,
            "Robotics": 5,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Dual Light Pulse Laser II": {
        "materials": {
            "Datacore - High Energy Physics": 1 / 0.436 / 10,
            "Datacore - Laser Physics": 1 / 0.436 / 10,
            "Dual Light Pulse Laser I": 1,
            "Morphite": 3,
            "Laser Focusing Crystals": 6,
            "Robotics": 1,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Gatling Pulse Laser II": {
        "materials": {
            "Datacore - High Energy Physics": 1 / 0.436 / 10,
            "Datacore - Laser Physics": 1 / 0.436 / 10,
            "Gatling Pulse Laser I": 1,
            "Morphite": 1,
            "Laser Focusing Crystals": 5,
            "Robotics": 5,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Small Focused Pulse Laser II": {
        "materials": {
            "Datacore - High Energy Physics": 1 / 0.436 / 10,
            "Datacore - Laser Physics": 1 / 0.436 / 10,
            "Small Focused Pulse Laser I": 1,
            "Morphite": 6,
            "Laser Focusing Crystals": 9,
            "Robotics": 1,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Electron Blaster Cannon II": {
        "materials": {
            "Datacore - Plasma Physics": 3 / 0.468 / 10,
            "Datacore - Quantum Physics": 3 / 0.468 / 10,
            "Electron Blaster Cannon I": 1,
            "Morphite": 32,
            "Particle Accelerator Unit": 30,
            "Robotics": 14,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Ion Blaster Cannon II": {
        "materials": {
            "Datacore - Plasma Physics": 3 / 0.468 / 10,
            "Datacore - Quantum Physics": 3 / 0.468 / 10,
            "Ion Blaster Cannon I": 1,
            "Morphite": 33,
            "Particle Accelerator Unit": 33,
            "Robotics": 14,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Neutron Blaster Cannon II": {
        "materials": {
            "Datacore - Plasma Physics": 3 / 0.468 / 10,
            "Datacore - Quantum Physics": 3 / 0.468 / 10,
            "Neutron Blaster Cannon I": 1,
            "Morphite": 15,
            "Particle Accelerator Unit": 35,
            "Robotics": 14,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Heavy Electron Blaster II": {
        "materials": {
            "Datacore - Plasma Physics": 2 / 0.468 / 10,
            "Datacore - Quantum Physics": 2 / 0.468 / 10,
            "Heavy Electron Blaster I": 1,
            "Morphite": 14,
            "Particle Accelerator Unit": 14,
            "Robotics": 5,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Heavy Ion Blaster II": {
        "materials": {
            "Datacore - Plasma Physics": 2 / 0.468 / 10,
            "Datacore - Quantum Physics": 2 / 0.468 / 10,
            "Heavy Ion Blaster I": 1,
            "Morphite": 17,
            "Particle Accelerator Unit": 17,
            "Robotics": 5,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Heavy Neutron Blaster II": {
        "materials": {
            "Datacore - Plasma Physics": 2 / 0.468 / 10,
            "Datacore - Quantum Physics": 2 / 0.468 / 10,
            "Heavy Neutron Blaster I": 1,
            "Morphite": 18,
            "Particle Accelerator Unit": 18,
            "Robotics": 5,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Light Electron Blaster II": {
        "materials": {
            "Datacore - Plasma Physics": 1 / 0.468 / 10,
            "Datacore - Quantum Physics": 1 / 0.468 / 10,
            "Light Electron Blaster I": 1,
            "Morphite": 3,
            "Particle Accelerator Unit": 6,
            "Robotics": 1,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Light Ion Blaster II": {
        "materials": {
            "Datacore - Plasma Physics": 1 / 0.468 / 10,
            "Datacore - Quantum Physics": 1 / 0.468 / 10,
            "Light Ion Blaster I": 1,
            "Morphite": 5,
            "Particle Accelerator Unit": 8,
            "Robotics": 1,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Light Neutron Blaster II": {
        "materials": {
            "Datacore - Plasma Physics": 1 / 0.468 / 10,
            "Datacore - Quantum Physics": 1 / 0.468 / 10,
            "Light Neutron Blaster I": 1,
            "Morphite": 6,
            "Particle Accelerator Unit": 9,
            "Robotics": 1,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "350mm Railgun II": {
        "materials": {
            "Datacore - Plasma Physics": 3 / 0.468 / 10,
            "Datacore - Quantum Physics": 3 / 0.468 / 10,
            "350mm Railgun I": 1,
            "Morphite": 33,
            "Superconductor Rails": 32,
            "Robotics": 14,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "425mm Railgun II": {
        "materials": {
            "Datacore - Plasma Physics": 3 / 0.468 / 10,
            "Datacore - Quantum Physics": 3 / 0.468 / 10,
            "425mm Railgun I": 1,
            "Morphite": 38,
            "Superconductor Rails": 36,
            "Robotics": 14,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Dual 250mm Railgun II": {
        "materials": {
            "Datacore - Plasma Physics": 3 / 0.468 / 10,
            "Datacore - Quantum Physics": 3 / 0.468 / 10,
            "Dual 250mm Railgun I": 1,
            "Morphite": 33,
            "Superconductor Rails": 32,
            "Robotics": 14,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "200mm Railgun II": {
        "materials": {
            "Datacore - Plasma Physics": 2 / 0.468 / 10,
            "Datacore - Quantum Physics": 2 / 0.468 / 10,
            "200mm Railgun I": 1,
            "Morphite": 5,
            "Superconductor Rails": 17,
            "Robotics": 5,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "250mm Railgun II": {
        "materials": {
            "Datacore - Plasma Physics": 2 / 0.468 / 10,
            "Datacore - Quantum Physics": 2 / 0.468 / 10,
            "250mm Railgun I": 1,
            "Morphite": 20,
            "Superconductor Rails": 20,
            "Robotics": 5,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Dual 150mm Railgun II": {
        "materials": {
            "Datacore - Plasma Physics": 2 / 0.468 / 10,
            "Datacore - Quantum Physics": 2 / 0.468 / 10,
            "Dual 150mm Railgun I": 1,
            "Morphite": 15,
            "Superconductor Rails": 15,
            "Robotics": 5,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "125mm Railgun II": {
        "materials": {
            "Datacore - Plasma Physics": 1 / 0.468 / 10,
            "Datacore - Quantum Physics": 1 / 0.468 / 10,
            "125mm Railgun I": 1,
            "Morphite": 5,
            "Superconductor Rails": 8,
            "Robotics": 1,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "150mm Railgun II": {
        "materials": {
            "Datacore - Plasma Physics": 1 / 0.468 / 10,
            "Datacore - Quantum Physics": 1 / 0.468 / 10,
            "150mm Railgun I": 1,
            "Morphite": 8,
            "Superconductor Rails": 11,
            "Robotics": 1,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "75mm Gatling Rail II": {
        "materials": {
            "Datacore - Plasma Physics": 1 / 0.468 / 10,
            "Datacore - Quantum Physics": 1 / 0.468 / 10,
            "75mm Gatling Rail I": 1,
            "Morphite": 1,
            "Superconductor Rails": 5,
            "Robotics": 1,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Cruise Missile Launcher II": {
        "materials": {
            "Datacore - Rocket Science": 3 / 0.425 / 10,
            "Datacore - Nuclear Physics": 3 / 0.425 / 10,
            "Cruise Missile Launcher I": 1,
            "Morphite": 12,
            "Quantum Microprocessor": 12,
            "Robotics": 12,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Heavy Assault Missile Launcher II": {
        "materials": {
            "Datacore - Rocket Science": 2 / 0.425 / 10,
            "Datacore - Nuclear Physics": 2 / 0.425 / 10,
            "Heavy Assault Missile Launcher I": 1,
            "Morphite": 6,
            "Quantum Microprocessor": 6,
            "Robotics": 6,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Heavy Missile Launcher II": {
        "materials": {
            "Datacore - Rocket Science": 2 / 0.425 / 10,
            "Datacore - Nuclear Physics": 2 / 0.425 / 10,
            "Heavy Missile Launcher I": 1,
            "Morphite": 6,
            "Quantum Microprocessor": 3,
            "Robotics": 6,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Light Missile Launcher II": {
        "materials": {
            "Datacore - Rocket Science": 1 / 0.425 / 10,
            "Datacore - Nuclear Physics": 1 / 0.425 / 10,
            "Light Missile Launcher I": 1,
            "Morphite": 3,
            "Quantum Microprocessor": 6,
            "Robotics": 3,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Rapid Heavy Missile Launcher II": {
        "materials": {
            "Datacore - Rocket Science": 6 / 0.425 / 10,
            "Datacore - Nuclear Physics": 6 / 0.425 / 10,
            "Rapid Heavy Missile Launcher I": 1,
            "Morphite": 14,
            "Quantum Microprocessor": 13,
            "Robotics": 11,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Rapid Light Missile Launcher II": {
        "materials": {
            "Datacore - Rocket Science": 2 / 0.425 / 10,
            "Datacore - Nuclear Physics": 2 / 0.425 / 10,
            "Rapid Light Missile Launcher I": 1,
            "Morphite": 3,
            "Quantum Microprocessor": 5,
            "Robotics": 3,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Rocket Launcher II": {
        "materials": {
            "Datacore - Rocket Science": 1 / 0.425 / 10,
            "Datacore - Nuclear Physics": 1 / 0.425 / 10,
            "Rocket Launcher I": 1,
            "Morphite": 1,
            "Quantum Microprocessor": 1,
            "Robotics": 1,
            "R.A.M.- Weapon Tech": 1,
        }
    },
    "Torpedo Launcher II": {
        "materials": {
            "Datacore - Rocket Science": 3 / 0.425 / 10,
            "Datacore - Nuclear Physics": 3 / 0.425 / 10,
            "Torpedo Launcher I": 1,
            "Morphite": 24,
            "Quantum Microprocessor": 24,
            "Robotics": 24,
            "R.A.M.- Weapon Tech": 1,
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
