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
        "UP": {"NAME": "Move up", "ID": 100, "KEY": event.KeySym.UP, "MOD": event.Modifier.LSHIFT},
        "DOWN": {"NAME": "Move down", "ID": 101, "KEY": event.KeySym.DOWN, "MOD": event.Modifier.LSHIFT},
        "LEFT": {"NAME": "Move left", "ID": 102, "KEY": event.KeySym.LEFT, "MOD": event.Modifier.LSHIFT},
        "RIGHT": {
            "NAME": "Move right",
            "ID": 103,
            "KEY": event.KeySym.RIGHT,
            "MOD": event.Modifier.LSHIFT,
        },
    },
    "Interaction": {
        "PERIOD + SHIFT": {
            "NAME": "Take stairs",
            "ID": 1,
            "KEY": event.KeySym.PERIOD,
            "MOD": event.Modifier.LSHIFT,
        },
        "C + SHIFT": {
            "NAME": "Consume ground item",
            "ID": 2,
            "KEY": event.KeySym.C,
            "MOD": event.Modifier.LSHIFT,
        },
        "T": {"NAME": "Trade with vendor", "ID": 3, "KEY": event.KeySym.T, "MOD": event.Modifier.NONE},
        "G": {"NAME": "Pickup stuff", "ID": 4, "KEY": event.KeySym.G, "MOD": event.Modifier.NONE},
    },
    "System": {
        "ESCAPE": {
            "NAME": "Exit game",
            "ID": 5,
            "KEY": event.KeySym.ESCAPE,
            "MOD": event.Modifier.NONE,
        },
    },
    "Menues": {
        "I": {"NAME": "Inventory", "ID": 6, "KEY": event.KeySym.I, "MOD": event.Modifier.NONE},
        "D": {
            "NAME": "Drop from Inventory",
            "ID": 7,
            "KEY": event.KeySym.D,
            "MOD": event.Modifier.NONE,
        },
        "C": {"NAME": "Character sheet", "ID": 8, "KEY": event.KeySym.C, "MOD": event.Modifier.NONE},
        "E": {"NAME": "Equipments", "ID": 9, "KEY": event.KeySym.E, "MOD": event.Modifier.NONE},
        "P": {"NAME": "Spellbook", "ID": 10, "KEY": event.KeySym.P, "MOD": event.Modifier.NONE},
        "L": {"NAME": "Consumption log", "ID": 11, "KEY": event.KeySym.L, "MOD": event.Modifier.NONE},
        "V": {"NAME": "Game history", "ID": 12, "KEY": event.KeySym.V, "MOD": event.Modifier.NONE},
    },
}


FOV = 20

TILE_SET = "Res/sprites.png"


class PlayerClass(Enum):
    FIGHTER = auto()
    MAGE = auto()
    ROUGE = auto()
    GENERIC = auto()
