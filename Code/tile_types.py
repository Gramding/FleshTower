from typing import Tuple
import numpy as np

from components import tileset

# this is like a structure in ABAP
# its got three headers with correspoing values
# ch: = the character in game
# fg: forground Color
# bg: Background color

graphic_dt = np.dtype(
    [
        ("ch", np.int32),
        ("fg", "3B"),
        ("bg", "3B"),
    ]
)

# another abap Structure :D
# walkable if it has collision
# transaprent if it blocks field of view
# dark represents the character on tile (uses above created struct type)

tile_dt = np.dtype(
    [
        ("walkable", np.bool),
        ("transparent", np.bool),
        ("dark", graphic_dt),
        ("light", graphic_dt),
    ]
)

# this is a helper function for tile creation


def new_tile(
    *,
    walkable: int,
    transparent: int,
    dark: Tuple[int, Tuple[int, int, int], Tuple[int, int, int]],
    light: Tuple[int, Tuple[int, int, int], Tuple[int, int, int]],
) -> np.ndarray:
    return np.array((walkable, transparent, dark, light), dtype=tile_dt)


# creation of new tiles (Floor and Wall)
# SHROUD for entire map not in fov
SHROUD = np.array((ord(" "), (255, 255, 255), (0, 0, 0)), dtype=graphic_dt)

stairs_up = new_tile(
    walkable=True,
    transparent=True,
    dark=(9005, (255, 255, 255), (0, 0, 0)),
    light=(9002, (255, 255, 255), (0, 0, 0)),
)


def randFloor() -> np.ndarray:
    floor = new_tile(
        walkable=True,
        transparent=True,
        dark=(9004, (255, 255, 255), (0, 0, 0)),
        light=(9001, (255, 255, 255), (0, 0, 0)),
    )
    return floor


def randWall() -> np.ndarray:
    wall = new_tile(
        walkable=False,
        transparent=False,
        dark=(9003, (255, 255, 255), (0, 0, 0)),
        light=(9000, (255, 255, 255), (0, 0, 0)),
    )
    return wall


def sprite_tile(*, walkable: bool, transparent: bool, sprite: int) -> np.ndarray:
    """A tile drawn with a sprite from Res/sprites.png, see components/tileset.py.
    White on black keeps the sprite's own colours."""
    return new_tile(
        walkable=walkable,
        transparent=transparent,
        dark=(sprite + tileset.DARK, (255, 255, 255), (0, 0, 0)),
        light=(sprite, (255, 255, 255), (0, 0, 0)),
    )


button_off = sprite_tile(walkable=False, transparent=False, sprite=tileset.SPRITE_LEVER_OFF)
button_on = sprite_tile(walkable=False, transparent=False, sprite=tileset.SPRITE_LEVER_ON)

door_closed = sprite_tile(walkable=False, transparent=False, sprite=tileset.SPRITE_DOOR_CLOSED)
door_open = sprite_tile(walkable=True, transparent=True, sprite=tileset.SPRITE_DOOR_OPEN)

chest_closed = sprite_tile(walkable=False, transparent=True, sprite=tileset.SPRITE_CHEST_CLOSED)
chest_open = sprite_tile(walkable=False, transparent=True, sprite=tileset.SPRITE_CHEST_OPEN)

plate_armed = new_tile(
    walkable=True,
    transparent=True,
    dark=(ord("^"), (120, 120, 120), (0, 0, 0)),
    light=(ord("^"), (200, 200, 200), (0, 0, 0)),
)

plate_spent = new_tile(
    walkable=True,
    transparent=True,
    dark=(ord("_"), (120, 120, 120), (0, 0, 0)),
    light=(ord("_"), (200, 200, 200), (0, 0, 0)),
)
