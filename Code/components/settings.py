from tcod import event
from enum import auto, Enum


CHEATS = True  # True for the ability to open cheats and so on
GENERAL_CHEATS = {
    "god_mode": False,
    "inf_mana": False,
    "inf_stamina": False,
    "noclip": False,
}
GENERAL_CHEAT_ACTIVATIONS = [
    "spawn_shop",
    "current_floor_+",
    "current_floor_-",
    "level_up",
]


# DONT CHANGE THE ID of the bind this is what determins what happens
# All here keys can be freely changed to whatever the KeySym allows

KEYBINDS = {
    "Movement": {
        "UP": {"NAME": "Move up", "ID": 100, "KEY": event.KeySym.UP, "MOD": 4097},
        "DOWN": {"NAME": "Move down", "ID": 101, "KEY": event.KeySym.DOWN, "MOD": 4097},
        "LEFT": {"NAME": "Move left", "ID": 102, "KEY": event.KeySym.LEFT, "MOD": 4097},
        "RIGHT": {
            "NAME": "Move right",
            "ID": 103,
            "KEY": event.KeySym.RIGHT,
            "MOD": 4097,
        },
    },
    "Interaction": {
        "PERIOD + SHIFT": {
            "NAME": "Take stairs",
            "ID": 1,
            "KEY": event.KeySym.PERIOD,
            "MOD": 4097,
        },
        "C + SHIFT": {
            "NAME": "Consume ground item",
            "ID": 2,
            "KEY": event.KeySym.C,
            "MOD": 4097,
        },
        "T": {"NAME": "Trade with vendor", "ID": 3, "KEY": event.KeySym.T, "MOD": 4096},
        "G": {"NAME": "Pickup stuff", "ID": 4, "KEY": event.KeySym.G, "MOD": 4096},
    },
    "System": {
        "ESCAPE": {
            "NAME": "Exit game",
            "ID": 5,
            "KEY": event.KeySym.ESCAPE,
            "MOD": 4096,
        },
    },
    "Menues": {
        "I": {"NAME": "Inventory", "ID": 6, "KEY": event.KeySym.I, "MOD": 4096},
        "D": {
            "NAME": "Drop from Inventory",
            "ID": 7,
            "KEY": event.KeySym.D,
            "MOD": 4096,
        },
        "C": {"NAME": "Character sheet", "ID": 8, "KEY": event.KeySym.C, "MOD": 4096},
        "E": {"NAME": "Equipments", "ID": 9, "KEY": event.KeySym.E, "MOD": 4096},
        "P": {"NAME": "Spellbook", "ID": 10, "KEY": event.KeySym.P, "MOD": 4096},
        "L": {"NAME": "Consumption log", "ID": 11, "KEY": event.KeySym.L, "MOD": 4096},
        "V": {"NAME": "Game history", "ID": 12, "KEY": event.KeySym.V, "MOD": 4096},
    },
}


FOV = 20

TILE_SET = "Res/sprites.png"


class PlayerClass(Enum):
    FIGHTER = auto()
    MAGE = auto()
    ROUGE = auto()
    GENERIC = auto()
