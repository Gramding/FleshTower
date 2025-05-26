#!/usr/bin/env python3
import tcod
from actions import EscapeAction, MovementAction
from input_handlers import EventHandler


def main() -> None:
    #setting screen size
    screen_width = 80
    screen_height = 50
    player_x = int(screen_width / 2)
    player_y = int(screen_height / 2)

    #this uses the file as a tileset
    tileset = tcod.tileset.load_tilesheet(
        "Res/dejavu10x10_gs_tc.png", 32,8, tcod.tileset.CHARMAP_TCOD
    )
    event_handler = EventHandler()
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
            #printing the character on screen
            root_console.print(x=player_x, y=player_y, string="@")
            #with this the screen is updated to now represent the changes made (character drawn)
            context.present(root_console)
            #clearing afterimages 
            root_console.clear()
            #this actions (user inputs)
            for event in tcod.event.wait():
                #create dispatcher
                action = event_handler.dispatch(event)
                #the event handler returns the class of correspoding event
                #if None event was not handeled
                if action is None:
                    continue
                #if event is instance of action class
                #handle movement and escape
                if isinstance(action, MovementAction):
                    player_x += action.dx
                    player_y += action.dy
                elif isinstance(action, EscapeAction):
                    raise SystemExit()

# this exits so that programm is run exlusivly through this file
# it checks for this beein the main file
if __name__ == "__main__":
    main()