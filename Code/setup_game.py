from __future__ import annotations

import copy
import lzma
import pickle
import traceback

from PIL import Image

from tcod import libtcodpy
import tcod

import numpy as np

import color
from engine import Engine
import entity_factory
import input_handlers
from game_map import GameWorld

from components.settings import KEYBINDS

background_image = np.asarray(Image.open("Res/main_menu.png").convert("RGB"))[:, :, :3]


def new_game() -> Engine:
    map_width = 200
    map_height = 100

    viewport_width = 80  # 80
    viewport_height = 50  # 43

    room_max_size = 20
    room_min_size = 12
    max_rooms = 50

    player = copy.deepcopy(entity_factory.player)

    engine = Engine(player=player)

    engine.game_world = GameWorld(
        engine=engine,
        max_rooms=max_rooms,
        room_min_size=room_min_size,
        room_max_size=room_max_size,
        map_width=map_width,
        map_height=map_height,
        viewport_height=viewport_height,
        viewport_width=viewport_width,
    )
    engine.game_world.generate_floor()
    engine.update_fov()

    engine.message_log.add_message("Flesh Tower", color.welcome_text)

    return engine


def load_game(filename: str) -> Engine:
    with open(filename, "rb") as f:
        engine = pickle.loads(lzma.decompress(f.read()))
    assert isinstance(engine, Engine)
    return engine


class MainMenu(input_handlers.BaseEventHandler):
    def on_render(self, console):
        console.draw_semigraphics(background_image, 0, 0)

        console.print(
            console.width // 2,
            console.height // 2 - 4,
            "FLESH TOWER",
            fg=color.menu_title,
            alignment=libtcodpy.CENTER,
        )

        menu_width = 24
        for i, text in enumerate([
            "[N] New try?",
            "[C] Continue last game",
            "[K] Keybinds",
            "[Q] Quit",
        ]):
            console.print(
                console.width // 2,
                console.height // 2 - 2 + i,
                text.ljust(menu_width),
                fg=color.menu_text,
                bg=color.black,
                alignment=libtcodpy.CENTER,
                bg_blend=libtcodpy.BKGND_ALPHA(64),
            )

    def ev_keydown(self, event):
        if event.sym in (tcod.event.KeySym.Q, tcod.event.KeySym.ESCAPE):
            raise SystemExit()
        elif event.sym == tcod.event.KeySym.C:
            try:
                return input_handlers.MainGameEventHandler(load_game("savegame.sav"))
            except FileNotFoundError:
                return input_handlers.PopupMessage(
                    self,
                    "The flesh does not remember youre presence",
                    halved=True,
                    alignment=libtcodpy.CENTER,
                )
            except Exception as exc:
                traceback.print_exc()
                return input_handlers.PopupMessage(
                    self,
                    f"Failed to load: \n{exc}",
                    halved=True,
                    alignment=libtcodpy.CENTER,
                )
        elif event.sym == tcod.event.KeySym.N:
            return input_handlers.MainGameEventHandler(new_game())
        elif event.sym == tcod.event.KeySym.K:
            text = ""
            for section in KEYBINDS:
                text = f"{text}{section}\n\n"
                for bind in KEYBINDS[section]:
                    text = f"{text}{bind}:{KEYBINDS[section][bind]}\n"
                text = f"{text}\n\n\n"

            return input_handlers.PopupMessage(
                self, text, halved=False, alignment=libtcodpy.CENTER
            )
