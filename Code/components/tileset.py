import tcod
from components.settings import TILE_SET


def get_tileset() -> tcod.tileset.Tileset:
    tileset = tcod.tileset.load_tilesheet(TILE_SET, 32, 10, tcod.tileset.CHARMAP_TCOD)
    tileset.remap(9000, 0, 5)  # new wall tile
    tileset.remap(9001, 1, 5)  # new floor tile
    tileset.remap(9002, 2, 5)  # new stairs tile
    tileset.remap(9003, 0, 6)  # new dark wall tile
    tileset.remap(9004, 1, 6)  # new dark floor tile
    tileset.remap(9005, 2, 6)  # new dark stairs tile

    return tileset
