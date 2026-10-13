import numpy as np
import tcod
from components.settings import TILE_SET

SPRITE_PLAYER = 9006
SPRITE_RAT = 9007
SPRITE_ZOMBIE = 9008
SPRITE_TROLL = 9009
SPRITE_CORPSE_FLY = 9010
SPRITE_EYE_SCREAMER = 9011
SPRITE_VISCERA_HOUND = 9012
SPRITE_VICERA_SPAWN = 9013
SPRITE_VENDOR = 9014
SPRITE_FLESH_GOLEM = 9015

SPRITE_HEALTH_POTION = 9016
SPRITE_LARGE_HEALTH_POTION = 9017
SPRITE_MANA_POTION = 9018
SPRITE_SCROLL = 9019
SPRITE_REMAINS = 9020

# (codepoint, column, row) on the sheet
_SPRITES = [
    (SPRITE_PLAYER, 0, 7),
    (SPRITE_RAT, 1, 7),
    (SPRITE_ZOMBIE, 2, 7),
    (SPRITE_TROLL, 3, 7),
    (SPRITE_CORPSE_FLY, 4, 7),
    (SPRITE_EYE_SCREAMER, 5, 7),
    (SPRITE_VISCERA_HOUND, 6, 7),
    (SPRITE_VICERA_SPAWN, 7, 7),
    (SPRITE_VENDOR, 8, 7),
    (SPRITE_FLESH_GOLEM, 9, 7),
    (SPRITE_HEALTH_POTION, 0, 8),
    (SPRITE_LARGE_HEALTH_POTION, 1, 8),
    (SPRITE_MANA_POTION, 2, 8),
    (SPRITE_SCROLL, 3, 8),
    (SPRITE_REMAINS, 4, 8),
]


def get_tileset() -> tcod.tileset.Tileset:
    tileset = tcod.tileset.load_tilesheet(TILE_SET, 32, 10, tcod.tileset.CHARMAP_TCOD)
    tileset.remap(9000, 0, 5)  # new wall tile
    tileset.remap(9001, 1, 5)  # new floor tile
    tileset.remap(9002, 2, 5)  # new stairs tile
    tileset.remap(9003, 0, 6)  # new dark wall tile
    tileset.remap(9004, 1, 6)  # new dark floor tile
    tileset.remap(9005, 2, 6)  # new dark stairs tile

    floor = tileset.get_tile(9001).astype(np.float32)
    for codepoint, column, row in _SPRITES:
        tileset.remap(codepoint, column, row)
        sprite = tileset.get_tile(codepoint).astype(np.float32)
        alpha = sprite[..., 3:4] / 255
        combined = sprite * alpha + floor * (1 - alpha)
        combined[..., 3] = 255
        tileset.set_tile(codepoint, combined.astype(np.uint8))

    return tileset