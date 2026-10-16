"""Every tile the level editor can place, in one table.

Level files store each cell as a TileDef.id, so ids must never change or be
reused. To add a tile, append a TileDef to TILES; the editor palette, the
editor rules and build_game_map all read from here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np

import tile_types


def is_yes(value) -> bool:
    return str(value).strip().lower() in ("yes", "true", "1")


@dataclass
class TileDef:
    id: int  # stored in level files, never change or reuse
    name: str
    char: str  # editor palette and brush glyph
    states: Dict[str, Callable[[], np.ndarray]]  # state -> game tile, first is the default
    color: Tuple[int, int, int] = (255, 255, 255)
    properties: List[Tuple[str, str]] = field(default_factory=list)  # editor fields
    solid: bool = False  # clears entities, can't go on the player start
    unique: bool = False  # only one per level, painting it again moves it
    link: Optional[str] = None  # "sends" or "receives" a link_id
    on_bump: Optional[str] = None  # name in actions.TILE_BUMPS
    start_state: Optional[Callable[[dict], str]] = None  # props -> state when the level loads
    on_link: Optional[Callable[[str, dict], str]] = None  # (state, props) -> state when its link fires
    on_step: bool = False  # the player stepping on it fires its link_id (plates)
    event: bool = False  # runs its "action" when its link fires (event markers, see events.py)
    extra_fields: Optional[Callable[[dict], List[Tuple[str, str]]]] = None  # fields that depend on props
    editor_char: bool = False  # show char instead of the game graphic in the editor

    @property
    def stateful(self) -> bool:
        """Needs its own entry in GameMap.tile_state at runtime."""
        return len(self.states) > 1 or bool(self.properties) or bool(self.on_bump)

    def fields_for(self, props: dict) -> List[Tuple[str, str]]:
        """Editor fields, including those that depend on the current values."""
        extra = self.extra_fields(props) if self.extra_fields else []
        return list(self.properties) + extra

    def initial_state(self, props: dict) -> str:
        if self.start_state is not None:
            return self.start_state(props)
        return next(iter(self.states))

    def make(self, state: Optional[str] = None) -> np.ndarray:
        return self.states[state or next(iter(self.states))]()


def door_start(props: dict) -> str:
    if is_yes(props.get("open")):
        return "open"
    return "hidden" if is_yes(props.get("hidden")) else "closed"


def door_on_link(state: str, props: dict) -> str:
    if state != "open":
        return "open"
    return "hidden" if is_yes(props.get("hidden")) else "closed"


def plate_start(props: dict) -> str:
    return "hidden" if is_yes(props.get("hidden")) else "armed"


# what an event marker can do, and the fields each action needs (run in events.py)
ACTION_FIELDS: Dict[str, List[Tuple[str, str]]] = {
    "message": [("text", "long_text")],
    "lore": [("lore", "lore")],
    "spawn": [("entity", "entity")],
    "teleport": [],
    "give_item": [("item_id", "quest_id"), ("item_name", "text")],
    "fire_signal": [("signal", "link_id")],
    "set_flag": [("flag", "flag"), ("value", "choice:on,off")],
    "end_level": [],
}
OPTIONAL_FIELDS = ("item_name", "value")  # action fields that may stay empty

# only react when these hold, checked by events.conditions_met
CONDITION_FIELDS: List[Tuple[str, str]] = [
    ("requires_flag", "flag"),
    ("requires_not_flag", "flag"),
    ("requires_item", "quest_id"),
]


# area triggers: a rectangle in the level that fires link_id when the player walks in
AREA_FIELDS: List[Tuple[str, str]] = [("link_id", "link_id"), ("repeat", "bool")] + CONDITION_FIELDS


def event_fields(props: dict) -> List[Tuple[str, str]]:
    action = ACTION_FIELDS.get(props.get("action", ""), [])
    return action + [("delay", "int")] + CONDITION_FIELDS


TILES: List[TileDef] = [
    TileDef(0, "Wall", "#", {"default": tile_types.randWall}, solid=True),
    TileDef(1, "Floor", ".", {"default": tile_types.randFloor}),
    TileDef(2, "Stairs", ">", {"default": lambda: tile_types.stairs_up}, unique=True),
    TileDef(
        3, "Button", "/",
        {"off": lambda: tile_types.button_off, "on": lambda: tile_types.button_on},
        color=(230, 200, 120),
        properties=[("link_id", "link_id")] + CONDITION_FIELDS,
        solid=True,
        link="sends",
        on_bump="lever",
    ),
    TileDef(
        4, "Door", "+",
        {
            "closed": lambda: tile_types.door_closed,
            "open": lambda: tile_types.door_open,
            "hidden": tile_types.randWall,
        },
        color=(180, 120, 70),
        properties=[
            ("link_id", "link_id"),
            ("hidden", "bool"),
            ("open", "bool"),
            ("key_id", "quest_id"),
            ("consume_key", "bool"),
        ],
        solid=True,
        link="receives",
        on_bump="door",
        start_state=door_start,
        on_link=door_on_link,
    ),
    TileDef(
        5, "Plate", "^",
        {
            "armed": lambda: tile_types.plate_armed,
            "spent": lambda: tile_types.plate_spent,
            "hidden": tile_types.randFloor,
        },
        color=(200, 200, 200),
        properties=[("link_id", "link_id"), ("hidden", "bool"), ("repeat", "bool")]
        + CONDITION_FIELDS,
        solid=True,  # keeps entities off the cell, the player can still walk on it
        link="sends",
        on_step=True,
        start_state=plate_start,
        editor_char=True,
    ),
    TileDef(
        6, "Event", "!",
        {"default": tile_types.randFloor},  # looks like floor in game
        color=(200, 80, 220),
        properties=[("link_id", "link_id"), ("action", "choice:" + ",".join(ACTION_FIELDS))],
        solid=True,
        link="receives",
        event=True,
        extra_fields=event_fields,
        editor_char=True,
    ),
]

TILE_BY_ID: Dict[int, TileDef] = {tile.id: tile for tile in TILES}
assert len(TILE_BY_ID) == len(TILES), "two tiles share an id"

# the editor itself relies on these three
TILE_WALL = 0
TILE_FLOOR = 1
TILE_STAIRS = 2

# props that hold ids, normalised when a level is built
ID_PROPERTIES = (
    "link_id", "key_id", "signal", "item_id",
    "flag", "requires_flag", "requires_not_flag", "requires_item",
)

# props holding a flag name, for autocomplete and checks
FLAG_PROPERTIES = ("flag", "requires_flag", "requires_not_flag")

# entity props that fire a signal (tiles send theirs through link_id)
SIGNAL_PROPERTIES = ("on_death", "on_pickup")

# fired by the level itself when it starts
START_SIGNAL = "start"
