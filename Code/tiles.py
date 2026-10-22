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
from rules import ACTIONS, CONDITION_FIELDS, LOCK_FIELDS


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
    link: Optional[str] = None  # "sends" or "receives" its signal
    link_optional: bool = False  # works without a signal, no warning (chests)
    on_bump: Optional[str] = None  # name in actions.TILE_BUMPS
    start_state: Optional[Callable[[dict], str]] = None  # props -> state when the level loads
    on_link: Optional[Callable[[str, dict], str]] = None  # (state, props) -> state when its signal fires
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


# area triggers: a rectangle in the level that fires its signal when the player
# walks in (also the invisible pressure plate: a 1x1 area)
AREA_FIELDS: List[Tuple[str, str]] = [("signal", "signal"), ("repeat", "bool")] + CONDITION_FIELDS


def event_fields(props: dict) -> List[Tuple[str, str]]:
    """The chosen action's fields (rules.ACTIONS), then delay and conditions."""
    action = ACTIONS.get(props.get("action", ""))
    return (action.fields if action else []) + [("delay", "int")] + CONDITION_FIELDS


TILES: List[TileDef] = [
    TileDef(0, "Wall", "#", {"default": tile_types.randWall}, solid=True),
    TileDef(1, "Floor", ".", {"default": tile_types.randFloor}),
    TileDef(2, "Stairs", ">", {"default": lambda: tile_types.stairs_up}, unique=True),
    TileDef(
        3, "Lever", "/",
        {"off": lambda: tile_types.button_off, "on": lambda: tile_types.button_on},
        color=(230, 200, 120),
        properties=[("signal", "signal")] + CONDITION_FIELDS,
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
        # conditions: what opening it by hand needs (a key is "requires");
        # a signal toggles it regardless
        properties=[("signal", "signal"), ("hidden", "bool"), ("open", "bool")] + LOCK_FIELDS,
        solid=True,
        link="receives",
        on_bump="door",
        start_state=door_start,
        on_link=door_on_link,
    ),
    # 5 was the pressure plate: removed, old plates load as 1x1 area triggers
    TileDef(
        6, "Event", "!",
        {"default": tile_types.randFloor},  # looks like floor in game
        color=(200, 80, 220),
        properties=[("signal", "signal"), ("action", "choice:" + ",".join(ACTIONS))],
        solid=True,
        link="receives",
        event=True,
        extra_fields=event_fields,
        editor_char=True,
    ),
    TileDef(
        7, "Chest", "=",
        {"closed": lambda: tile_types.chest_closed, "open": lambda: tile_types.chest_open},
        color=(200, 150, 60),
        properties=[
            ("loot_table", "loot_table"),  # see components/loot.py
            ("gives", "gives"),  # always in it: a data item or a quest item
            ("signal", "signal"),  # fired when opened
        ]
        + LOCK_FIELDS,
        solid=True,
        link="sends",
        link_optional=True,
        on_bump="chest",
    ),
]

TILE_BY_ID: Dict[int, TileDef] = {tile.id: tile for tile in TILES}
assert len(TILE_BY_ID) == len(TILES), "two tiles share an id"

# the editor itself relies on these three
TILE_WALL = 0
TILE_FLOOR = 1
TILE_STAIRS = 2

PLATE_ID = 5  # removed tile, see rules / level_editor upgrades

# props that hold ids, normalised when a level is built ("item" of gives may
# be a case-sensitive data id, rules.act_gives normalises quest ids itself)
ID_PROPERTIES = ("signal", "target", "flag", "if", "ifnot", "requires")

# props holding a flag name, for autocomplete and checks
FLAG_PROPERTIES = ("flag", "if", "ifnot")

# entity props that fire a signal (tiles and areas send their "signal")
SIGNAL_PROPERTIES = ("on_death", "on_pickup")

# fired by the level itself when it starts
START_SIGNAL = "start"
