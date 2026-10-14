from __future__ import annotations

import lzma
import os
import pickle
import re
import traceback
from typing import Callable, Dict, List, Optional, Tuple, TYPE_CHECKING

import numpy as np
import tcod
from tcod import libtcodpy

import color
import entity_factory
import input_handlers
import tile_types
from components.settings import (
    LEVEL_DIR,
    LEVEL_EXTENSION,
    LEVEL_HEIGHT,
    LEVEL_WIDTH,
)
from entity import Actor, Item

if TYPE_CHECKING:
    from engine import Engine
    from game_map import GameMap

LEVEL_FORMAT_VERSION = 1

TILE_WALL = 0
TILE_FLOOR = 1
TILE_STAIRS = 2
TILE_NAMES = {TILE_WALL: "Wall", TILE_FLOOR: "Floor", TILE_STAIRS: "Stairs"}

BRUSH_TILE = "tile"
BRUSH_START = "start"
BRUSH_ENTITY = "entity"

# graphics of each tile id, indexable with the whole tile grid at once
TILE_GRAPHICS = np.array(
    [
        tile_types.randWall()["light"],
        tile_types.randFloor()["light"],
        tile_types.stairs_up["light"],
    ],
    dtype=tile_types.graphic_dt,
)

NAME_MAX_LENGTH = 24
NAME_PATTERN = re.compile(r"^[A-Za-z0-9 _\-]+$")

# screen layout of the editor (screen is 80x50)
VIEW_WIDTH = 60
VIEW_HEIGHT = 50
PANEL_X = VIEW_WIDTH
PANEL_WIDTH = 20
PALETTE_ROWS = 16

CURSOR_BG = (150, 40, 40)
RECT_BG = (90, 30, 90)
START_BG = (40, 90, 40)
PANEL_HIGHLIGHT = (90, 20, 20)

SHIFT = tcod.event.Modifier.LSHIFT | tcod.event.Modifier.RSHIFT
CTRL = tcod.event.Modifier.LCTRL | tcod.event.Modifier.RCTRL

class CustomLevel:
    def __init__(self, name: str = "", width: int = LEVEL_WIDTH, height: int = LEVEL_HEIGHT):
        self.name = name
        self.width = width
        self.height = height
        self.tiles = np.full((width, height), TILE_WALL, dtype=np.uint8, order="F")
        self.player_start: Tuple[int, int] = (width // 2, height // 2)
        self.entities: Dict[Tuple[int, int], str] = {}

    @classmethod
    def new_default(cls) -> CustomLevel:
        """Empty level with one room in the middle and the player inside."""
        level = cls()
        cx, cy = level.width // 2, level.height // 2
        level.tiles[cx - 6 : cx + 7, cy - 5 : cy + 6] = TILE_FLOOR
        level.player_start = (cx, cy)
        return level

    @property
    def stairs_location(self) -> Optional[Tuple[int, int]]:
        found = np.argwhere(self.tiles == TILE_STAIRS)
        if len(found) == 0:
            return None
        return int(found[0][0]), int(found[0][1])

    def save_as(self, filename: str) -> None:
        save_data = lzma.compress(pickle.dumps(self))
        with open(filename, "wb") as f:
            f.write(save_data)

def level_file_name(name: str) -> str:
    return os.path.join(LEVEL_DIR, name.strip().replace(" ","_") + LEVEL_EXTENSION)

def save_level(level: CustomLevel) -> str:
    os.makedirs(LEVEL_DIR, exist_ok=True)
    filename = level_file_name(level.name)
    level.save_as(filename=filename)
    return filename

def load_level(filename: str) -> CustomLevel:
    with open(filename, "rb") as f:
        level = pickle.loads(lzma.decompress(f.read()))
    assert isinstance(level, CustomLevel)
    print(level.entities)
    return level

def list_levels() -> List[Tuple[str,str]]:
    os.makedirs(LEVEL_DIR, exist_ok=True)
    files = [
        os.path.join(LEVEL_DIR, f)
        for f in os.listdir(LEVEL_DIR)
        if f.endswith(LEVEL_EXTENSION)
    ]
    files.sort(key=os.path.getmtime, reverse=True)
    results = []
    for filename in files:
        display = os.path.basename(filename)[: -len(LEVEL_EXTENSION)].replace(" ","_")
        results.append((display, filename))
    return results

def build_game_map(level: CustomLevel, engine: Engine) -> Tuple[GameMap, int]:
    from game_map import GameMap

    player = engine.player
    dungeon = GameMap(engine, level.width, level.height, entities=[player])
    dungeon.tiles[level.tiles == TILE_FLOOR] = tile_types.randFloor()
    dungeon.tiles[level.tiles == TILE_STAIRS] = tile_types.stairs_up

    stairs = level.stairs_location
    dungeon.upstairs_location = stairs if stairs else (-1,-1)

    player.place(*level.player_start, dungeon)

    missing = 0
    for (x, y), attr in level.entities.items():
        prototype = getattr(entity_factory, attr, None)
        if not isinstance(prototype, (Actor, Item)):
            missing += 1
            continue
        spawned = prototype.spawn(dungeon, x, y)
    print("missing:", missing)
    print("on map:", [e.name for e in dungeon.entities])     
    return dungeon, missing

def new_custom_game(level:CustomLevel) -> Engine:
    import procgen
    from setup_game import create_engine

    engine = create_engine(current_floor=0)
    engine.item_chances = procgen.item_chances
    engine.enemy_chances = procgen.enemy_chances
    engine.game_map, missing = build_game_map(level,engine)
    engine.update_fov()

    engine.message_log.add_message("Flesh Tower", color.welcome_text)
    engine.message_log.add_message(f"You awaken in {level.name}")
    if missing:
        engine.message_log.add_message(
            f"{missing} entities of this level no longer exist", color.impossible
        )
    if level.stairs_location is None:
        engine.message_log.add_message("There are no stairs in this level", color.impossible)

    return engine


def event_tile(event) -> Optional[Tuple[int,int]]:
    try:
        tile = event.tile
    except Exception:
        return None
    if tile is None:
        return None
    return int(tile[0]), int(tile[1])





def key_to_char(event) -> Optional[str]:
    sym = int(event.sym)
    shifted = bool(event.mod & SHIFT)
    if ord("a") <= sym <= ord("z"):
        char = chr(sym)
        return char.upper() if shifted else char
    if ord("0") <= sym <= ord("9") and not shifted:
        return chr(sym)
    if sym == int(tcod.event.KeySym.SPACE):
        return " "
    if sym == int(tcod.event.KeySym.MINUS):
        return "_" if shifted else "-"
    return None

class TextPrompt(input_handlers.BaseEventHandler):
    def __init__(
        self,
        parent: input_handlers.BaseEventHandler,
        title: str,
        text: str,
        on_submit: Callable[[str], Optional[input_handlers.BaseEventHandler]],
    ):
        self.parent = parent
        self.title = title
        self.text = text
        self.on_submit = on_submit
        self.error = ""

    def on_render(self, console):
        self.parent.on_render(console)
        input_handlers.dim(console)
        width = NAME_MAX_LENGTH + 8
        x, y = input_handlers.draw_box(console, width, 7, self.title)
        console.print(x + 2, y + 2, (self.text + "_").ljust(NAME_MAX_LENGTH + 1),
                      fg=color.menu_title, bg=(40, 10, 10))
        console.print(x + 2, y + 4, "[Enter] ok  [Esc] cancel", fg=color.impossible)
        if self.error:
            console.print(x + 2, y + 5, self.error[: width - 4], fg=color.error)

    def ev_keydown(self, event):
        key = event.sym
        if key == tcod.event.KeySym.ESCAPE:
            return self.parent
        if key in input_handlers.CONFIRM_KEYS:
            return self.on_submit(self.text.strip())
        if key == tcod.event.KeySym.BACKSPACE:
            self.text = self.text[:-1]
            self.error = ""
            return None
        char = key_to_char(event)
        if char and len(self.text) < NAME_MAX_LENGTH:
            self.text += char
            self.error = ""
        return None



class LevelMenu(input_handlers.BaseEventHandler):
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

    def load_current(self) -> CustomLevel:
        display, filename = self.current()
        return load_level(filename)

    def ev_keydown(self, event):
        key = event.sym
        if key == tcod.event.KeySym.ESCAPE:
            return self.main_menu
        if key == tcod.event.KeySym.UP and self.levels:
            self.selected = (self.selected - 1) % len(self.levels)
        elif key == tcod.event.KeySym.DOWN and self.levels:
            self.selected = (self.selected + 1) % len(self.levels)
        elif key == tcod.event.KeySym.N:
            return LevelEditor(self, CustomLevel.new_default())
        elif self.current() is None:
            return None
        elif key in input_handlers.CONFIRM_KEYS or key == tcod.event.KeySym.P:
            try:
                return input_handlers.MainGameEventHandler(new_custom_game(self.load_current()))
            except Exception as exc:
                traceback.print_exc()
                return self.popup(f"Failed to load:\n{exc}")
        elif key == tcod.event.KeySym.E:
            try:
                return LevelEditor(self, self.load_current())
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
            return TextPrompt(self, "Rename level", display, self.rename)
        return None

    def rename(self, new_name: str):
        display, filename = self.current()
        problem = check_name(new_name)
        if problem:
            return self.popup(problem)
        new_filename = level_file_name(new_name)
        if os.path.exists(new_filename) and new_filename != filename:
            return self.popup(f"{new_name} already exists")
        level = load_level(filename)
        level.name = new_name
        save_level(level)
        if new_filename != filename:
            os.remove(filename)
        self.refresh()
        return self


def check_name(name: str) -> str:
    if not name:
        return "The level needs a name"
    if not NAME_PATTERN.match(name):
        return "Use letters, numbers, space, - and _"
    return ""



class LevelEditor(input_handlers.BaseEventHandler):
    def __init__(self, level_menu: LevelMenu, level: CustomLevel):
        self.level_menu = level_menu
        self.level = level
        self.dirty = False

        self.palette = entity_factory.build_palette()
        self.groups = list(self.palette.keys())
        self.group_index = 0
        self.palette_index = {group: 0 for group in self.groups}

        self.brush = BRUSH_TILE
        self.brush_tile = TILE_FLOOR
        self.rect_mode = False
        self.rect_anchor: Optional[Tuple[int, int]] = None

        self.mouse: Optional[Tuple[int, int]] = None  # screen tile under mouse
        self.held_button: Optional[int] = None  # 1 left, 3 right

        self.status = "Shape the flesh. [S] saves."
        self.center_camera(*level.player_start)


    def center_camera(self, x: int, y: int) -> None:
        self.cam_x = x - VIEW_WIDTH // 2
        self.cam_y = y - VIEW_HEIGHT // 2
        self.clamp_camera()

    def clamp_camera(self) -> None:
        self.cam_x = max(0, min(self.cam_x, self.level.width - VIEW_WIDTH))
        self.cam_y = max(0, min(self.cam_y, self.level.height - VIEW_HEIGHT))

    def map_pos(self) -> Optional[Tuple[int, int]]:
        """Map tile under the mouse, None when over the side panel."""
        if self.mouse is None:
            return None
        sx, sy = self.mouse
        if not (0 <= sx < VIEW_WIDTH and 0 <= sy < VIEW_HEIGHT):
            return None
        x, y = sx + self.cam_x, sy + self.cam_y
        if not (0 <= x < self.level.width and 0 <= y < self.level.height):
            return None
        return x, y


    @property
    def group(self) -> str:
        return self.groups[self.group_index]

    def selected_entity(self) -> Tuple[str, object]:
        entries = self.palette[self.group]
        return entries[self.palette_index[self.group]]

    def cycle_entity(self, step: int) -> None:
        entries = self.palette[self.group]
        self.palette_index[self.group] = (self.palette_index[self.group] + step) % len(entries)
        self.brush = BRUSH_ENTITY

    def brush_label(self) -> str:
        if self.brush == BRUSH_TILE:
            return TILE_NAMES[self.brush_tile]
        if self.brush == BRUSH_START:
            return "Player start"
        return entity_factory.short_name(self.selected_entity()[1])

    def brush_glyph(self) -> Tuple[str, Tuple[int, int, int]]:
        """What the cursor looks like, a preview of the current brush."""
        if self.brush == BRUSH_TILE:
            return {TILE_WALL: "#", TILE_FLOOR: ".", TILE_STAIRS: ">"}[self.brush_tile], color.white
        if self.brush == BRUSH_START:
            return "@", color.white
        prototype = self.selected_entity()[1]
        return prototype.char, prototype.color


    def paint(self, x: int, y: int) -> None:
        level = self.level
        if self.brush == BRUSH_TILE:
            if self.brush_tile == TILE_WALL:
                if (x, y) == level.player_start:
                    self.status = "Can't wall in the start"
                    return
                level.entities.pop((x, y), None)
            if self.brush_tile == TILE_STAIRS:
                old = level.stairs_location
                if old and old != (x, y):
                    level.tiles[old] = TILE_FLOOR
                    self.status = "Stairs moved (one per level)"
            if level.tiles[x, y] != self.brush_tile:
                level.tiles[x, y] = self.brush_tile
                self.dirty = True
        elif self.brush == BRUSH_START:
            if level.player_start != (x, y):
                level.entities.pop((x, y), None)
                level.player_start = (x, y)
                if level.tiles[x, y] == TILE_WALL:
                    level.tiles[x, y] = TILE_FLOOR
                self.dirty = True
        else:
            if (x, y) == level.player_start:
                self.status = "The player stands there"
                return
            attr = self.selected_entity()[0]
            if level.entities.get((x, y)) != attr:
                level.entities[(x, y)] = attr
                if level.tiles[x, y] == TILE_WALL:
                    level.tiles[x, y] = TILE_FLOOR
                self.dirty = True

    def erase(self, x: int, y: int) -> None:
        level = self.level
        if (x, y) in level.entities:
            del level.entities[(x, y)]
            self.dirty = True
        elif (x, y) == level.player_start:
            self.status = "Move the start with [4]"
        elif level.tiles[x, y] != TILE_WALL:
            level.tiles[x, y] = TILE_WALL
            self.dirty = True

    def fill_rect(self, a: Tuple[int, int], b: Tuple[int, int], erase: bool) -> None:
        x1, x2 = sorted((a[0], b[0]))
        y1, y2 = sorted((a[1], b[1]))
        for x in range(x1, x2 + 1):
            for y in range(y1, y2 + 1):
                if erase:
                    self.erase(x, y)
                elif self.brush == BRUSH_START or (
                    self.brush == BRUSH_TILE and self.brush_tile == TILE_STAIRS
                ):
                    self.paint(b[0], b[1])
                    return
                else:
                    self.paint(x, y)

    def apply_at_mouse(self) -> None:
        pos = self.map_pos()
        if pos is None or self.held_button is None or self.rect_mode:
            return
        if self.held_button == 1:
            self.paint(*pos)
        elif self.held_button == 3:
            self.erase(*pos)


    def ask_save(self, then_leave: bool = False):
        def submit(name: str):
            problem = check_name(name)
            if problem:
                prompt.error = problem
                return None
            filename = level_file_name(name)
            same_file = self.level.name and filename == level_file_name(self.level.name)
            if os.path.exists(filename) and not same_file:
                return input_handlers.PopupToConfirm(
                    self, f"Overwrite {name}?", lambda: self.save_as(name, then_leave)
                )
            return self.save_as(name, then_leave)

        prompt = TextPrompt(self, "Save level as", self.level.name, submit)
        return prompt

    def save_as(self, name: str, then_leave: bool = False):
        self.level.name = name
        try:
            save_level(self.level)
        except Exception as exc:
            traceback.print_exc()
            self.status = f"Save failed: {exc}"
            return self
        self.dirty = False
        self.status = f"Saved {name}"
        if self.level.stairs_location is None:
            self.status += ". No stairs yet!"
        self.level_menu.refresh()
        if then_leave:
            return self.leave()
        return self

    def leave(self):
        self.level_menu.refresh()
        return self.level_menu

    def ev_quit(self, event):
        if self.dirty:
            name = self.level.name or "autosave"
            self.level.name = name
            try:
                save_level(self.level)
                print(f"Unsaved level written to {level_file_name(name)}")
            except Exception:
                traceback.print_exc()
        raise SystemExit()

    def ev_mousemotion(self, event):
        self.mouse = event_tile(event)
        self.apply_at_mouse()

    def ev_mousebuttondown(self, event):
        tile = event_tile(event)
        if tile is not None:
            self.mouse = tile
        self.held_button = int(event.button)
        if self.rect_mode:
            self.rect_anchor = self.map_pos()
        else:
            self.apply_at_mouse()

    def ev_mousebuttonup(self, event):
        if self.rect_mode and self.rect_anchor is not None:
            end = self.map_pos()
            if end is not None:
                self.fill_rect(self.rect_anchor, end, erase=self.held_button == 3)
        self.rect_anchor = None
        self.held_button = None

    def ev_mousewheel(self, event):
        step = -1 if event.y > 0 else 1
        over_panel = self.mouse is not None and self.mouse[0] >= PANEL_X
        if over_panel:
            self.cycle_entity(step)
        else:
            self.cam_y += step * 3
            self.clamp_camera()
            self.apply_at_mouse()

    def ev_keydown(self, event):
        key = event.sym
        mod = event.mod
        k = tcod.event.KeySym

        pan = 10 if mod & SHIFT else 1
        if key == k.UP:
            self.cam_y -= pan
        elif key == k.DOWN:
            self.cam_y += pan
        elif key == k.LEFT:
            self.cam_x -= pan
        elif key == k.RIGHT:
            self.cam_x += pan
        elif key == k.N1:
            self.brush, self.brush_tile = BRUSH_TILE, TILE_WALL
        elif key == k.N2:
            self.brush, self.brush_tile = BRUSH_TILE, TILE_FLOOR
        elif key == k.N3:
            self.brush, self.brush_tile = BRUSH_TILE, TILE_STAIRS
        elif key == k.N4:
            self.brush = BRUSH_START
        elif key == k.N5:
            self.brush = BRUSH_ENTITY
        elif key == k.TAB:
            self.group_index = (self.group_index + 1) % len(self.groups)
            self.brush = BRUSH_ENTITY
        elif key in (k.LEFTBRACKET, k.PAGEUP):
            self.cycle_entity(-1)
        elif key in (k.RIGHTBRACKET, k.PAGEDOWN):
            self.cycle_entity(1)
        elif key == k.R:
            self.rect_mode = not self.rect_mode
            self.rect_anchor = None
            self.status = "Rectangle mode" if self.rect_mode else "Paint mode"
        elif key == k.C:
            self.center_camera(*self.level.player_start)
        elif key == k.S:
            return self.ask_save()
        elif key == k.ESCAPE:
            if self.dirty:
                return input_handlers.PopupToConfirm(self, "Leave without saving?", self.leave)
            return self.leave()
        self.clamp_camera()
        self.apply_at_mouse()
        return None


    def on_render(self, console):
        level = self.level
        cx, cy = self.cam_x, self.cam_y
        view = level.tiles[cx : cx + VIEW_WIDTH, cy : cy + VIEW_HEIGHT]
        console.rgb[0 : view.shape[0], 0 : view.shape[1]] = TILE_GRAPHICS[view]

        for (x, y), attr in level.entities.items():
            sx, sy = x - cx, y - cy
            if 0 <= sx < VIEW_WIDTH and 0 <= sy < VIEW_HEIGHT:
                prototype = getattr(entity_factory, attr, None)
                if prototype is None:
                    console.print(sx, sy, "?", fg=color.error)
                else:
                    console.print(sx, sy, prototype.char, fg=prototype.color)

        px, py = level.player_start[0] - cx, level.player_start[1] - cy
        if 0 <= px < VIEW_WIDTH and 0 <= py < VIEW_HEIGHT:
            console.print(px, py, "@", fg=color.white, bg=START_BG)

        pos = self.map_pos()
        if self.rect_anchor is not None and pos is not None:
            x1, x2 = sorted((self.rect_anchor[0], pos[0]))
            y1, y2 = sorted((self.rect_anchor[1], pos[1]))
            sx1, sx2 = max(x1 - cx, 0), min(x2 - cx + 1, VIEW_WIDTH)
            sy1, sy2 = max(y1 - cy, 0), min(y2 - cy + 1, VIEW_HEIGHT)
            area = console.rgb[sx1:sx2, sy1:sy2]
            area["ch"] = ord("." if self.held_button == 1 else "x")
            area["fg"] = color.white
            area["bg"] = RECT_BG
        if pos is not None:
            char, fg = self.brush_glyph()
            console.print(pos[0] - cx, pos[1] - cy, char, fg=fg, bg=CURSOR_BG)

        self.render_panel(console, pos)

    def render_panel(self, console, pos: Optional[Tuple[int, int]]) -> None:
        x = PANEL_X
        w = PANEL_WIDTH
        console.draw_frame(x=x, y=0, width=w, height=console.height,
                           title="Editor", clear=True, fg=color.white, bg=color.black)
        inner = w - 2
        title = (self.level.name or "<unnamed>") + ("*" if self.dirty else "")
        console.print(x + 1, 1, title[:inner], fg=color.menu_title)

        console.print(x + 1, 3, "Brush:", fg=color.impossible)
        console.print(x + 1, 4, self.brush_label()[:inner])
        mode = "Rectangle" if self.rect_mode else "Paint"
        console.print(x + 1, 5, f"Mode: {mode}"[:inner])
        if pos is not None:
            console.print(x + 1, 6, f"x {pos[0]} y {pos[1]}", fg=color.impossible)
            attr = self.level.entities.get(pos)
            if attr:
                prototype = getattr(entity_factory, attr, None)
                label = entity_factory.short_name(prototype) if prototype else attr
                console.print(x + 1, 7, label[:inner], fg=color.impossible)

        console.print(x + 1, 9, f"<{self.group}> Tab"[:inner], fg=color.menu_title)
        entries = self.palette[self.group]
        current = self.palette_index[self.group]
        first = max(0, min(current - PALETTE_ROWS // 2, len(entries) - PALETTE_ROWS))
        for row, (attr, prototype) in enumerate(entries[first : first + PALETTE_ROWS]):
            index = first + row
            y = 10 + row
            label = f" {entity_factory.short_name(prototype)}"[: inner - 1].ljust(inner - 1)
            selected = index == current
            bg = PANEL_HIGHLIGHT if selected and self.brush == BRUSH_ENTITY else (
                (40, 40, 40) if selected else color.black)
            console.print(x + 1, y, prototype.char, fg=prototype.color, bg=bg)
            console.print(x + 2, y, label, fg=color.white, bg=bg)

        help_lines = [
            "1 wall  "
            "2 floor",
            "3 stairs "
            "4 start",
            "5 entity [ ] pick",
            "LMB draw RMB erase",
            "R rectangle mode",
            "Arrows pan (Shift)",
            "Wheel scroll/pick",
            "C center on start",
            "S save  Esc back",
        ]
        help_y = 11 + PALETTE_ROWS + 1
        for i, line in enumerate(help_lines):
            console.print(x + 1, help_y + i, line[:inner], fg=color.impossible)

        status_y = console.height - 4
        for i in range(0, min(len(self.status), inner * 3), inner):
            console.print(x + 1, status_y + i // inner, self.status[i : i + inner], fg=color.menu_title)