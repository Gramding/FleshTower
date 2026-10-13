from __future__ import annotations

import lzma
import os
import pickle
import re
import traceback
from typing import Callable, Dict, List, Optional, Tuple, TYPE_CHECKING

import numpy as np
import tcod
from tcod import libtcodpy

import color
import entity_factory
import input_handlers
import tile_types
from components.settings import (
    LEVEL_DIR,
    LEVEL_EXTENSION,
    LEVEL_HEIGHT,
    LEVEL_WIDTH,
)
from entity import Actor, Item

if TYPE_CHECKING:
    from engine import Engine
    from game_map import GameMap

LEVEL_FORMAT_VERSION = 1

TILE_WALL = 0
TILE_FLOOR = 1
TILE_STAIRS = 2
TILE_NAMES = {TILE_WALL: "Wall", TILE_FLOOR: "Floor", TILE_STAIRS: "Stairs"}

# graphics of each tile id, indexable with the whole tile grid at once
TILE_GRAPHICS = np.array(
    [
        tile_types.randWall()["light"],
        tile_types.randFloor()["light"],
        tile_types.stairs_up["light"],
    ],
    dtype=tile_types.graphic_dt,
)

NAME_MAX_LENGTH = 24
NAME_PATTERN = re.compile(r"^[A-Za-z0-9 _\-]+$")

# screen layout of the editor (screen is 80x50)
VIEW_WIDTH = 60
VIEW_HEIGHT = 50
PANEL_X = VIEW_WIDTH
PANEL_WIDTH = 20
PALETTE_ROWS = 16

CURSOR_BG = (150, 40, 40)
RECT_BG = (90, 30, 90)
START_BG = (40, 90, 40)
PANEL_HIGHLIGHT = (90, 20, 20)

SHIFT = tcod.event.Modifier.LSHIFT | tcod.event.Modifier.RSHIFT
CTRL = tcod.event.Modifier.LCTRL | tcod.event.Modifier.RCTRL

class CustomLevel:
    def __init__(self, name: str = "", width: int = LEVEL_WIDTH, height: int = LEVEL_HEIGHT):
        self.name = name
        self.width = width
        self.height = height
        self.tiles = np.full((width, height), TILE_WALL, dtype=np.uint8, order="F")
        self.player_start: Tuple[int, int] = (width // 2, height // 2)
        self.entities: Dict[Tuple[int, int], str] = {}

    @classmethod
    def new_default(cls) -> CustomLevel:
        """Empty level with one room in the middle and the player inside."""
        level = cls()
        cx, cy = level.width // 2, level.height // 2
        level.tiles[cx - 6 : cx + 7, cy - 5 : cy + 6] = TILE_FLOOR
        level.player_start = (cx, cy)
        return level

    @property
    def stairs_location(self) -> Optional[Tuple[int, int]]:
        found = np.argwhere(self.tiles == TILE_STAIRS)
        if len(found) == 0:
            return None
        return int(found[0][0]), int(found[0][1])

    def save_as(self, filename: str) -> None:
        save_data = lzma.compress(pickle.dumps(self))
        with open(filename, "wb") as f:
            f.write(save_data)

def level_file_name(name: str) -> str:
    return os.path.join(LEVEL_DIR, name.strip().replace(" ","_") + LEVEL_EXTENSION)

def save_level(level: CustomLevel) -> str:
    os.makedirs(LEVEL_DIR, exist_ok=True)
    filename = level_file_name(level.name)
    level.save_as(filename=filename)
    return filename

def load_level(filename: str) -> CustomLevel:
    with open(filename, "rb") as f:
        level = pickle.loads(lzma.decompress(f.read()))
    assert isinstance(level, CustomLevel)
    return level

def list_levels() -> List[Tuple[str,str]]:
    if not os.path.isdir(LEVEL_DIR):
        return
    files = [
        os.path.join(LEVEL_DIR, f)
        for f in os.listdir(LEVEL_DIR)
        if f.endswith(LEVEL_EXTENSION)
    ]
    files.sort(key=os.path.getmtime, reverse=True)
    results = []
    for filename in files:
        display = os.path.basename(filename)[: -len(LEVEL_EXTENSION)].replace(" ","_")
        results.append((display),(filename))
    return results

def build_game_map(level: CustomLevel, engine: Engine) -> Tuple[GameMap, int]:
    from game_map import GameMap

    player = engine.player
    dungeon = GameMap(engine, level.width, level.height, entities=[player])
    dungeon.tiles[level.tiles == TILE_FLOOR] = tile_types.randFloor()
    dungeon.tiles[level.tiles == TILE_STAIRS] = tile_types.stairs_up

    stairs = level.stairs_location
    dungeon.upstairs_location = stairs if stairs else (-1,-1)

    player.place(*level.player_start, dungeon)

    missing = 0
    for (x, y), attr in level.entities.items():
        prototype = getattr(entity_factory, attr, None)
        if not isinstance(prototype, (Actor, Item)):
            missing += 1
            continue

    return dungeon, missing

