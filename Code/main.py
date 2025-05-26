#!/usr/bin/env python3
import tcod
from engine import Engine
from input_handlers import EventHandler
from game_map import GameMap
from entity import Entity


def main() -> None:
    #setting screen size
    screen_width = 80
    screen_height = 50

    map_width = 80
    map_height = 45

    #this uses the file as a tileset
    tileset = tcod.tileset.load_tilesheet(
        "Res/dejavu10x10_gs_tc.png", 32,8, tcod.tileset.CHARMAP_TCOD
    )
    event_handler = EventHandler()
    player = Entity(int(screen_width / 2), int(screen_height / 2), "@",(255,255,255))
    npc = Entity(int(screen_width / 2 - 5), int(screen_height / 2), "K", (255,255,0))
    entities = {npc,player}
    game_map = GameMap(map_width, map_height)
    engine = Engine(entities=entities, event_handler=event_handler,game_map=game_map,player=player)
    #this creates the screen (the game window)
    #screen size and name are passed
    #the with expression is used for resource management
    with tcod.context.new_terminal(
        screen_width,
        screen_height,
        tileset=tileset,
        title="Flesh Tower",
        vsync=True
    ) as context:
        #this creates the console in wich the game is displayed
        root_console = tcod.Console(screen_width, screen_height, order="F")
        #the game loop
        while True:
            engine.render(console=root_console,context=context)
            events = tcod.event.wait()
            engine.handle_events(events=events)
            

# this exits so that programm is run exlusivly through this file
# it checks for this beein the main file
if __name__ == "__main__":
    main()