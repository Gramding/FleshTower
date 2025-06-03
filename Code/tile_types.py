from typing import Tuple
import numpy as np
import random

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
    dark=(ord("<"), (0, 0, 100), (132, 38, 7)),
    light=(ord("<"), (255, 255, 255), (219, 63, 11)),
)


def randFloor() -> np.ndarray:
    dark_i = random.randint(30, 50)
    light_i = random.randint(50, 70)
    floor = new_tile(
        walkable=True,
        transparent=True,
        dark=(ord(" "), (255, 255, 255), (dark_i, 51, 49)),
        light=(ord(" "), (255, 255, 255), (light_i, 18, 3)),
    )
    return floor


def randWall() -> np.ndarray:
    dark_i = random.randint(70, 80)
    light_i = random.randint(0, 10)
    wall = new_tile(
        walkable=False,
        transparent=False,
        dark=(ord(" "), (255, 255, 255), (50, 92, dark_i)),
        light=(ord(" "), (255, 255, 255), (92, 26, light_i)),
    )
    return wall
