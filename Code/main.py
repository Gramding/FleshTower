#!/usr/bin/env python3
import tcod
import color
import traceback
import exceptions
import input_handlers

from components.tileset import get_tileset

import setup_game


def screens_below(handler):
    """The handler and the screens it was opened over: popups and menus keep
    the screen behind them in .parent (or .editor for level editor menus)."""
    seen = set()
    while handler is not None and id(handler) not in seen:
        seen.add(id(handler))
        yield handler
        handler = getattr(handler, "parent", None) or getattr(handler, "editor", None)


def save_game(handler: input_handlers.BaseEventHandler, filename: str) -> None:
    for screen in screens_below(handler):
        if isinstance(screen, input_handlers.EventHandler):
            if screen.engine.player.is_alive:
                screen.engine.save_as(filename)
                print("The Flesh remembers this point in time")
            return
        if hasattr(screen, "level") and getattr(screen, "dirty", False):
            # a level editor behind a popup: same autosave as its own ev_quit
            from level_editor import save_level, level_file_name

            screen.level.name = screen.level.name or "autosave"
            save_level(screen.level)
            print(f"Unsaved level written to {level_file_name(screen.level.name)}")
            return


def main() -> None:
    # setting screen size
    screen_width = 80
    screen_height = 50

    tileset = get_tileset()

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
