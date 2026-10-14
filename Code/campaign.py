import os
from typing import List, Optional, Tuple
from components.settings import CAMPAIGN_DIR, CAMPAIGN_EXTENSTION

import input_handlers
import color
import tcod
import traceback
from tcod import libtcodpy


# screen layout of the campaign select screen (screen is 80x50)
VIEW_WIDTH = 60
VIEW_HEIGHT = 50
PANEL_X = VIEW_WIDTH
PANEL_WIDTH = 20
PANEL_HIGHLIGHT = (90, 20, 20)
PALETTE_ROWS = 16

class CampaignMenu(input_handlers.BaseEventHandler):
    def __init__(self, main_menu: input_handlers.BaseEventHandler):
        self.main_menu = main_menu
        self.selected = 0
        self.refresh()

    def refresh(self) -> None:
        self.levels = list_levels()
        self.selected = max(0, min(self.selected,len(self.levels) - 1 ))

    def popup(self, text:str) -> input_handlers.BaseEventHandler:
        return input_handlers.PopupMessage(self,text,halved=True,alignment=libtcodpy.CENTER)

    def on_render(self, console):
        self.main_menu.on_render(console)
        input_handlers.dim(console)
        width, height = 60,30
        x,y = input_handlers.draw_box(console,width,height,"Custom Level Select")
        visible_rows = height - 9
        if not self.levels:
            console.print(x + 2 , y + 2, "No custom levels", fg=color.impossible)
            console.print(x + 2, y + 3, "Press [N] cave a new Floor into the Tower.", fg=color.impossible)
        first = max(0,self.selected - visible_rows + 1)
        for row, (display, _) in enumerate(self.levels[first : first + visible_rows]):
            index = first + row
            text  = f" {display}"[: width - 4].ljust(width - 4)
            if index == self.selected:
                console.print(x + 2, y + 2 + row, text, fg=color.menu_title, bg=PANEL_HIGHLIGHT)
            else:
                console.print(x + 2, y + 2 + row, text, fg=color.menu_text)

        help_y = y + height - 6
        console.print(x + 2, help_y, "[Enter] play      [E] edit", fg=color.menu_text)
        console.print(x + 2, help_y + 1, "[N] new level     [R] rename", fg=color.menu_text)
        console.print(x + 2, help_y + 2, "[Del] delete      [Esc] back", fg=color.menu_text)
        console.print(x + 2, help_y + 3, "Up/Down to choose", fg=color.impossible)


    def current(self) -> Optional[Tuple[str, str]]:
        if not self.levels:
            return None
        return self.levels[self.selected]

    # def load_current(self) -> CustomLevel:
    #     display, filename = self.current()
    #     return load_level(filename)

    def ev_keydown(self, event):
        key = event.sym
        if key == tcod.event.KeySym.ESCAPE:
            return self.main_menu
        if key == tcod.event.KeySym.UP and self.levels:
            self.selected = (self.selected - 1) % len(self.levels)
        elif key == tcod.event.KeySym.DOWN and self.levels:
            self.selected = (self.selected + 1) % len(self.levels)
        elif key == tcod.event.KeySym.N:
            #return LevelEditor(self, CustomLevel.new_default())
            pass
        elif self.current() is None:
            return None
        elif key in input_handlers.CONFIRM_KEYS or key == tcod.event.KeySym.P:
            try:
                #return input_handlers.MainGameEventHandler(new_custom_game(self.load_current()))
                #TODO
                pass
            except Exception as exc:
                traceback.print_exc()
                return self.popup(f"Failed to load:\n{exc}")
        elif key == tcod.event.KeySym.E:
            try:
                #return LevelEditor(self, self.load_current())
                #TODO
                pass
            except Exception as exc:
                traceback.print_exc()
                return self.popup(f"Failed to load:\n{exc}")
        elif key in (tcod.event.KeySym.DELETE, tcod.event.KeySym.BACKSPACE):
            display, filename = self.current()

            def delete():
                os.remove(filename)
                self.refresh()
                return self

            return input_handlers.PopupToConfirm(self, f"Delete {display}?", delete)
        elif key == tcod.event.KeySym.R:
            display, filename = self.current()
            return input_handlers.TextPrompt(self, "Rename level", display, self.rename)
        return None

    def rename(self, new_name: str):
        display, filename = self.current()
        problem = input_handlers.check_name(new_name)
        if problem:
            return self.popup(problem)
        # new_filename = level_file_name(new_name)
        # if os.path.exists(new_filename) and new_filename != filename:
        #     return self.popup(f"{new_name} already exists")
        # level = load_level(filename)
        # level.name = new_name
        # save_level(level)
        # if new_filename != filename:
        #     os.remove(filename)
        # self.refresh()
        # return self



def list_levels() -> List[Tuple[str,str]]:
    os.makedirs(CAMPAIGN_DIR, exist_ok=True)
    files = [
        os.path.join(CAMPAIGN_DIR, f)
        for f in os.listdir(CAMPAIGN_DIR)
        if f.endswith(CAMPAIGN_EXTENSTION)
    ]
    files.sort(key=os.path.getmtime, reverse=True)
    results = []
    for filename in files:
        display = os.path.basename(filename)[: -len(CAMPAIGN_EXTENSTION)].replace(" ","_")
        results.append((display, filename))
    return results