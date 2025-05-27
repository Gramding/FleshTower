#!/usr/bin/env python3
import tcod
import copy
from engine import Engine
from input_handlers import EventHandler
import entity_factory
from procgen import generate_dungeon


def main() -> None:
    # setting screen size
    screen_width = 80
    screen_height = 50

    map_width = 80
    map_height = 45

    room_max_size = 10
    room_min_size = 6
    max_rooms = 30

    max_monsters_per_room = 2

    # this uses the file as a tileset
    tileset = tcod.tileset.load_tilesheet(
        "Res/dejavu10x10_gs_tc.png", 32, 8, tcod.tileset.CHARMAP_TCOD
    )
    player = copy.deepcopy(entity_factory.player)
    engine = Engine(player=player)
    # generates the map with given parameters
    engine.game_map = generate_dungeon(
        max_rooms=max_rooms,
        room_min_size=room_min_size,
        room_max_size=room_max_size,
        map_width=map_width,
        map_height=map_height,
        max_monsters_per_room=max_monsters_per_room,
        engine=engine,
    )
    engine.update_fov()
    # this creates the screen (the game window)
    # screen size and name are passed
    # the with expression is used for resource management
    with tcod.context.new_terminal(
        screen_width, screen_height, tileset=tileset, title="Flesh Tower", vsync=True
    ) as context:
        # this creates the console in wich the game is displayed
        root_console = tcod.console.Console(screen_width, screen_height, order="F")
        # the game loop
        while True:
            engine.render(console=root_console, context=context)
            engine.event_handler.handle_events()


# this exits so that programm is run exlusivly through this file
# it checks for this beein the main file
if __name__ == "__main__":
    main()
