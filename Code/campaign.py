from __future__ import annotations
import copy
import lzma
import os
import pickle
from typing import TYPE_CHECKING, List, Optional, Tuple
from components.settings import CAMPAIGN_DIR, CAMPAIGN_EXTENSTION

import input_handlers
import color
import tcod
import traceback
from tcod import libtcodpy

from level_editor import CustomLevel, load_level
from level_editor import list_levels

if TYPE_CHECKING:
    from engine import Engine
    from game_map import GameMap


# screen layout of the campaign select screen (screen is 80x50)
VIEW_WIDTH = 60
VIEW_HEIGHT = 50
PANEL_X = VIEW_WIDTH
PANEL_WIDTH = 20
PANEL_HIGHLIGHT = (90, 20, 20)
PALETTE_ROWS = 16

class Campaign:
    def __init__(self, name: str = ""):
        self.name = name
        self.levels: List[CustomLevel] = []
        self.current = -1  # index of the level being played, -1 = not started

    def next_level(self) -> Optional[CustomLevel]:
        self.current += 1
        if self.current < len(self.levels):
            return self.levels[self.current]
        return None

    def save_as(self, filename: str) -> None:
        save_data = lzma.compress(pickle.dumps(self))
        with open(filename, "wb") as f:
            f.write(save_data)

class CampaignMenu(input_handlers.BaseEventHandler):
    def __init__(self, main_menu: input_handlers.BaseEventHandler):
        self.main_menu = main_menu
        self.selected = 0
        self.refresh()

    def refresh(self) -> None:
        self.campaigns = list_campaigns()
        self.selected = max(0, min(self.selected,len(self.campaigns) - 1 ))

    def popup(self, text:str) -> input_handlers.BaseEventHandler:
        return input_handlers.PopupMessage(self,text,halved=True,alignment=libtcodpy.CENTER)

    def on_render(self, console):
        self.main_menu.on_render(console)
        input_handlers.dim(console)
        width, height = 60,30
        x,y = input_handlers.draw_box(console,width,height,"Custom Campaign Select")
        visible_rows = height - 9
        if not self.campaigns:
            console.print(x + 2 , y + 2, "No custom campaigns", fg=color.impossible)
            console.print(x + 2, y + 3, "Press [N] to create new campaign from campaigns.", fg=color.impossible)
        first = max(0,self.selected - visible_rows + 1)
        for row, (display, _) in enumerate(self.campaigns[first : first + visible_rows]):
            index = first + row
            text  = f" {display}"[: width - 4].ljust(width - 4)
            if index == self.selected:
                console.print(x + 2, y + 2 + row, text, fg=color.menu_title, bg=PANEL_HIGHLIGHT)
            else:
                console.print(x + 2, y + 2 + row, text, fg=color.menu_text)

        help_y = y + height - 6
        console.print(x + 2, help_y, "[Enter] play      [E] edit", fg=color.menu_text)
        console.print(x + 2, help_y + 1, "[N] new campaign  [R] rename", fg=color.menu_text)
        console.print(x + 2, help_y + 2, "[Del] delete      [Esc] back", fg=color.menu_text)
        console.print(x + 2, help_y + 3, "Up/Down to choose", fg=color.impossible)


    def current(self) -> Optional[Tuple[str, str]]:
        if not self.campaigns:
            return None
        return self.campaigns[self.selected]

    def load_current(self) -> Campaign:
         display, filename = self.current()
         return load_campaign(filename)

    def ev_keydown(self, event):
        key = event.sym
        if key == tcod.event.KeySym.ESCAPE:
            return self.main_menu
        if key == tcod.event.KeySym.UP and self.campaigns:
            self.selected = (self.selected - 1) % len(self.campaigns)
        elif key == tcod.event.KeySym.DOWN and self.campaigns:
            self.selected = (self.selected + 1) % len(self.campaigns)
        elif key == tcod.event.KeySym.N:
            return CampaignEditor(self, Campaign())
        elif self.current() is None:
            return None
        elif key in input_handlers.CONFIRM_KEYS or key == tcod.event.KeySym.P:
            try:
                return input_handlers.resume_game(new_campaign_game(self.load_current()))
            except Exception as exc:
                traceback.print_exc()
                return self.popup(f"Failed to load:\n{exc}")
        elif key == tcod.event.KeySym.E:
            try:
                return CampaignEditor(self, self.load_current())
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
            return input_handlers.TextPrompt(self, "Rename campaign", display, self.rename)
        return None

    def rename(self, new_name: str):
        display, filename = self.current()
        problem = input_handlers.check_name(new_name)
        if problem:
            return self.popup(problem)
        new_filename = campaign_file_name(new_name)
        if os.path.exists(new_filename) and new_filename != filename:
            return self.popup(f"{new_name} already exists")
        campaign = load_campaign(filename)
        campaign.name = new_name
        save_campaign(campaign)
        if new_filename != filename:
            os.remove(filename)
        self.refresh()
        return self



def list_campaigns() -> List[Tuple[str,str]]:
    os.makedirs(CAMPAIGN_DIR, exist_ok=True)
    files = [
        os.path.join(CAMPAIGN_DIR, f)
        for f in os.listdir(CAMPAIGN_DIR)
        if f.endswith(CAMPAIGN_EXTENSTION)
    ]
    files.sort(key=os.path.getmtime, reverse=True)
    results = []
    for filename in files:
        display = os.path.basename(filename)[: -len(CAMPAIGN_EXTENSTION)].replace("_"," ")
        results.append((display, filename))
    return results

def campaign_file_name(name: str) -> str:
    return os.path.join(CAMPAIGN_DIR, name.strip().replace(" ","_") + CAMPAIGN_EXTENSTION)



def save_campaign(level: Campaign) -> str:
    os.makedirs(CAMPAIGN_DIR, exist_ok=True)
    filename = campaign_file_name(level.name)
    level.save_as(filename=filename)
    return filename


def load_campaign(filename: str) -> Campaign:
    with open(filename, "rb") as f:
        campaign = pickle.loads(lzma.decompress(f.read()))
    assert isinstance(campaign, Campaign)
    return campaign


def campaign_filename(name: str) -> str:
    return os.path.join(CAMPAIGN_DIR, name.strip().replace(" ", "_") + CAMPAIGN_EXTENSTION)

class CampaignEditor(input_handlers.BaseEventHandler):
    def __init__(self, campaign_menu: CampaignMenu, campaign: Campaign):
        self.campaign_menu = campaign_menu
        self.campaign = campaign
        self.available = list_levels()  # (display, filename)
        self.focus = 0  # 0 = level list, 1 = campaign order
        self.cursor = [0, 0]
        self.dirty = False
        self.status = "Enter adds a level"

    def column(self, index: int) -> List[str]:
        if index == 0:
            return [display for display, _ in self.available]
        return [level.name for level in self.campaign.levels]

    def clamp(self) -> None:
        for i in (0, 1):
            size = len(self.column(i))
            self.cursor[i] = max(0, min(self.cursor[i], size - 1))

    def add_selected(self) -> None:
        if not self.available:
            return
        display, filename = self.available[self.cursor[0]]
        level = load_level(filename)
        if level.stairs_location is None:
            self.status = f"{display} has no stairs"
            return
        self.campaign.levels.append(level)
        self.cursor[1] = len(self.campaign.levels) - 1
        self.dirty = True
        self.status = f"Added {display}"

    def remove_selected(self) -> None:
        if not self.campaign.levels:
            return
        removed = self.campaign.levels.pop(self.cursor[1])
        self.dirty = True
        self.status = f"Removed {removed.name}"
        self.clamp()

    def move_selected(self, step: int) -> None:
        levels = self.campaign.levels
        i = self.cursor[1]
        j = i + step
        if 0 <= i < len(levels) and 0 <= j < len(levels):
            levels[i], levels[j] = levels[j], levels[i]
            self.cursor[1] = j
            self.dirty = True

    def ask_save(self):
        def submit(name: str):
            problem = input_handlers.check_name(name)
            if problem:
                prompt.error = problem
                return None
            if not self.campaign.levels:
                prompt.error = "Add at least one level"
                return None
            filename = campaign_filename(name)
            own_file = self.campaign.name and filename == campaign_filename(self.campaign.name)
            if os.path.exists(filename) and not own_file:
                return input_handlers.PopupToConfirm(
                    self, f"Overwrite {name}?", lambda: self.save_as(name)
                )
            return self.save_as(name)

        prompt = input_handlers.TextPrompt(self, "Save campaign as", self.campaign.name, submit)
        return prompt

    def save_as(self, name: str):
        os.makedirs(CAMPAIGN_DIR, exist_ok=True)
        self.campaign.name = name
        self.campaign.save_as(campaign_filename(name))
        self.dirty = False
        self.status = f"Saved {name}"
        self.campaign_menu.refresh()
        return self

    def leave(self):
        self.campaign_menu.refresh()
        return self.campaign_menu

    def ev_keydown(self, event):
        key = event.sym
        k = tcod.event.KeySym
        shift = event.mod & tcod.event.Modifier.SHIFT

        if key == k.ESCAPE:
            if self.dirty:
                return input_handlers.PopupToConfirm(self, "Leave without saving?", self.leave)
            return self.leave()
        if key in (k.TAB, k.LEFT, k.RIGHT):
            self.focus = 1 - self.focus
        elif key in (k.UP, k.DOWN):
            step = -1 if key == k.UP else 1
            if shift and self.focus == 1:
                self.move_selected(step)
            else:
                self.cursor[self.focus] += step
        elif key in input_handlers.CONFIRM_KEYS and self.focus == 0:
            self.add_selected()
        elif key in (k.DELETE, k.BACKSPACE) and self.focus == 1:
            self.remove_selected()
        elif key == k.S:
            return self.ask_save()
        self.clamp()
        return None

    def on_render(self, console):
        self.campaign_menu.on_render(console)
        input_handlers.dim(console)
        width, height = 70, 36
        title = (self.campaign.name or "<unnamed>") + ("*" if self.dirty else "")
        x, y = input_handlers.draw_box(console, width, height, f"Campaign: {title}")

        col_width = (width - 6) // 2
        visible_rows = height - 11
        headers = ["Levels", "Campaign order"]
        for col in (0, 1):
            cx = x + 2 + col * (col_width + 2)
            header_fg = color.menu_title if col == self.focus else color.impossible
            console.print(cx, y + 2, headers[col], fg=header_fg)

            items = self.column(col)
            if not items:
                empty = "No levels saved" if col == 0 else "Empty"
                console.print(cx, y + 4, empty, fg=color.impossible)
            first = max(0, self.cursor[col] - visible_rows + 1)
            for row, name in enumerate(items[first : first + visible_rows]):
                index = first + row
                label = f"{index + 1}. {name}" if col == 1 else name
                text = f" {label}"[:col_width].ljust(col_width)
                if col == self.focus and index == self.cursor[col]:
                    console.print(cx, y + 4 + row, text, fg=color.menu_title, bg=PANEL_HIGHLIGHT)
                else:
                    console.print(cx, y + 4 + row, text, fg=color.menu_text)

        help_y = y + height - 6
        console.print(x + 2, help_y, "Tab/Left/Right switch    [Enter] add level", fg=color.menu_text)
        console.print(x + 2, help_y + 1, "Shift+Up/Down reorder    [Del] remove", fg=color.menu_text)
        console.print(x + 2, help_y + 2, "[S] save                 [Esc] back", fg=color.menu_text)
        console.print(x + 2, help_y + 4, self.status[: width - 4], fg=color.menu_title)


def new_campaign_game(campaign: Campaign) -> Engine:
    import procgen
    from setup_game import create_engine

    campaign = copy.deepcopy(campaign)
    campaign.current = -1

    engine = create_engine()
    engine.item_chances = procgen.item_chances
    engine.enemy_chances = procgen.enemy_chances
    engine.game_world.campaign = campaign
    engine.game_world.generate_floor()
    engine.update_fov()

    engine.message_log.add_message(campaign.name, color.welcome_text)
    return engine