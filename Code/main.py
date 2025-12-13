#!/usr/bin/env python3
import tcod
import color
import traceback
import exceptions
import input_handlers

import setup_game


def save_game(handler: input_handlers.BaseEventHandler, filename: str) -> None:
    if isinstance(handler, input_handlers.EventHandler):
        handler.engine.save_as(filename)
        print("The Flesh remembers this point in time")


def main() -> None:
    # setting screen size
    screen_width = 80
    screen_height = 50

    # this uses the file as a tileset
    tileset = tcod.tileset.load_tilesheet(
        "Res/dejavu10x10_gs_tc.png", 32, 8, tcod.tileset.CHARMAP_TCOD
    )
    handler: input_handlers.BaseEventHandler = setup_game.MainMenu()
    # this creates the screen (the game window)
    # screen size and name are passed
    # the with expression is used for resource management
    with tcod.context.new(
        columns=screen_width,
        rows=screen_height,
        tileset=tileset,
        title="Flesh Tower",
        vsync=True,
    ) as context:
        # this creates the console in wich the game is displayed
        root_console = tcod.console.Console(screen_width, screen_height, order="F")
        # the game loop
        try:
            while True:
                root_console.clear()
                handler.on_render(console=root_console)
                context.present(root_console)

                try:
                    for event in tcod.event.wait():
                        context.convert_event(event)
                        handler = handler.handle_events(event)
                except Exception:  # Handle exceptions in game.
                    traceback.print_exc()  # Print error to stderr.
                    # Then print the error to the message log.
                    if isinstance(handler, input_handlers.EventHandler):
                        handler.engine.message_log.add_message(
                            traceback.format_exc(), color.error
                        )
        except exceptions.QuitWithoutSaving:
            raise
        except SystemExit:  # Save and quit.
            save_game(handler, "savegame.sav")
            raise
        except BaseException:  # Save on any other unexpected exception.
            save_game(handler, "savegame.sav")
            raise


# this exits so that programm is run exlusivly through this file
# it checks for this beeing the main file
if __name__ == "__main__":
    main()
