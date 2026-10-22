from __future__ import annotations

import copy
import lzma
import os
import pickle
import re
import traceback
from collections import deque
from typing import Callable, Dict, List, Optional, Tuple, TYPE_CHECKING

from components.dialouge_parser import load_dialogue, quest_key
from components import loot

import numpy as np
import tcod
from tcod import libtcodpy

import color
import entity_factory
import input_handlers
import tile_types
from tiles import (
    TileDef,
    TILES,
    TILE_BY_ID,
    TILE_WALL,
    TILE_FLOOR,
    TILE_STAIRS,
    ID_PROPERTIES,
    SIGNAL_PROPERTIES,
    START_SIGNAL,
    is_yes,
)
from components.settings import (
    LEVEL_DIR,
    LEVEL_EXTENSION,
    LEVEL_HEIGHT,
    LEVEL_WIDTH,
    DIALOGUE_DIR,
    LORE_DIR,
)
from entity import Actor, Item

if TYPE_CHECKING:
    from engine import Engine
    from game_map import GameMap

LEVEL_FORMAT_VERSION = 1

BRUSH_TILE = "tile"
BRUSH_START = "start"
BRUSH_ENTITY = "entity"
BRUSH_SELECT = "select"
BRUSH_AREA = "area"

TILE_GROUP = "Tiles"  # palette group of TILES, the rest are entity groups


def build_tile_graphics() -> np.ndarray:
    """Graphics of each tile id, indexable with the whole tile grid at once.
    Ids without a tile show as a magenta '?'."""
    unknown = np.array(
        (ord("?"), (255, 0, 255), (0, 0, 0)), dtype=tile_types.graphic_dt
    )
    graphics = np.full(max(TILE_BY_ID) + 1, unknown, dtype=tile_types.graphic_dt)
    for tile in TILES:
        if tile.editor_char:  # e.g. event markers look like floor in game
            graphics[tile.id] = (ord(tile.char), tile.color, (0, 0, 0))
        else:
            graphics[tile.id] = tile.make()["light"]
    return graphics


TILE_GRAPHICS = build_tile_graphics()

NAME_MAX_LENGTH = 24
NAME_PATTERN = re.compile(r"^[A-Za-z0-9 _\-]+$")

# screen layout of the editor (screen is 80x50)
VIEW_WIDTH = 60
VIEW_HEIGHT = 50
PANEL_X = VIEW_WIDTH
PANEL_WIDTH = 20
PANEL_HIGHLIGHT = (90, 20, 20)
PALETTE_ROWS = 16

CURSOR_BG = (150, 40, 40)
RECT_BG = (90, 30, 90)
START_BG = (40, 90, 40)
LINK_BG = (30, 60, 110)
AREA_BG = (60, 50, 10)


SHIFT = tcod.event.Modifier.LSHIFT | tcod.event.Modifier.RSHIFT
CTRL = tcod.event.Modifier.LCTRL | tcod.event.Modifier.RCTRL


class CustomLevel:
    def __init__(
        self, name: str = "", width: int = LEVEL_WIDTH, height: int = LEVEL_HEIGHT
    ):
        self.name = name
        self.width = width
        self.height = height
        self.tiles = np.full((width, height), TILE_WALL, dtype=np.uint8, order="F")
        self.player_start: Tuple[int, int] = (width // 2, height // 2)
        self.entities: Dict[Tuple[int, int], str] = {}
        self.properties: Dict[Tuple[int, int], Dict[str, str]] = {}
        # area triggers: {"rect": (x1, y1, x2, y2), "props": {...}}, see tiles.AREA_FIELDS
        self.areas: List[dict] = []

    def __setstate__(self, state):
        self.__dict__.update(state)
        if not isinstance(self.__dict__.get("properties"), dict):
            self.properties = {}
        if "areas" not in self.__dict__:
            self.areas = []

    def area_at(self, pos) -> Optional[dict]:
        """The last drawn area containing pos."""
        for area in reversed(self.areas):
            x1, y1, x2, y2 = area["rect"]
            if x1 <= pos[0] <= x2 and y1 <= pos[1] <= y2:
                return area
        return None

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
    return os.path.join(LEVEL_DIR, name.strip().replace(" ", "_") + LEVEL_EXTENSION)


def save_level(level: CustomLevel) -> str:
    os.makedirs(LEVEL_DIR, exist_ok=True)
    filename = level_file_name(level.name)
    level.save_as(filename=filename)
    return filename


def load_level(filename: str) -> CustomLevel:
    with open(filename, "rb") as f:
        level = pickle.loads(lzma.decompress(f.read()))
    assert isinstance(level, CustomLevel)
    return level


def list_levels() -> List[Tuple[str, str]]:
    os.makedirs(LEVEL_DIR, exist_ok=True)
    files = [
        os.path.join(LEVEL_DIR, f)
        for f in os.listdir(LEVEL_DIR)
        if f.endswith(LEVEL_EXTENSION)
    ]
    files.sort(key=os.path.getmtime, reverse=True)
    results = []
    for filename in files:
        display = os.path.basename(filename)[: -len(LEVEL_EXTENSION)].replace(" ", "_")
        results.append((display, filename))
    return results


def all_levels(current=None) -> List[CustomLevel]:
    """Every saved level, with the one open in the editor replacing its saved copy."""
    levels = []
    for _, filename in list_levels():
        try:
            level = load_level(filename)
        except Exception:
            continue
        if current is not None and current.name and level.name == current.name:
            continue  # the open version replaces the saved one
        levels.append(level)
    if current is not None:
        levels.append(current)
    return levels


def find_lore_users(lore_file, current=None, skip_pos=None, key="lore") -> List[str]:
    """Everything, in any level, whose property key names this file
    (lore items for "lore", chests for "loot_table")."""
    users = []
    for level in all_levels(current):
        for pos, props in getattr(level, "properties", {}).items():
            if level is current and pos == skip_pos:
                continue
            if props.get(key) == lore_file:
                users.append(f"{level.name or 'this level'}: {pos[0]},{pos[1]}")
    return users


def find_quest_id(quest_id, current=None, skip_pos=None):
    from components.dialouge_parser import quest_key, list_dialogues, load_dialogue

    quest_id = quest_key(quest_id)
    produced, used = [], []

    for level in all_levels(current):
        name = level.name or "this level"
        for pos, props in getattr(level, "properties", {}).items():
            if level is current and pos == skip_pos:
                continue
            attr = level.entities.get(pos, "?")
            if quest_key(props.get("quest_id", "")) == quest_id:
                produced.append(f"{name}: {attr} on the floor")
            if quest_key(props.get("drop_id", "")) == quest_id:
                produced.append(f"{name}: dropped by {attr}")
            if quest_key(props.get("key_id", "")) == quest_id:
                used.append(f"{name}: unlocks door at {pos[0]},{pos[1]}")

    for _, filename in list_dialogues():
        try:
            dialogue = load_dialogue(os.path.join(DIALOGUE_DIR, filename))
        except Exception:
            continue
        for passage in dialogue.passages.values():
            for tag in passage.tags:
                kind, _, value = tag.partition(":")
                if quest_key(value) != quest_id:
                    continue
                if kind == "gives":
                    produced.append(f"{filename}: gives in '{passage.name}'")
                elif kind in ("requires", "takes"):
                    used.append(f"{filename}: {kind} in '{passage.name}'")
    return produced, used


def tile_at(level, pos) -> Optional[TileDef]:
    return TILE_BY_ID.get(int(level.tiles[pos]))


def signal_users(level):
    """Everything in this level that sends or receives a signal,
    as (signal, "sends"/"receives", label, pos)."""
    for pos, props in level.properties.items():
        tile = tile_at(level, pos)
        link_id = quest_key(props.get("link_id", ""))
        if link_id and tile is not None and tile.link:
            yield link_id, tile.link, tile.name, pos
        attr = level.entities.get(pos)
        for key in SIGNAL_PROPERTIES:
            signal = quest_key(props.get(key, ""))
            if signal and attr:
                yield signal, "sends", f"{attr} {key}", pos
        signal = quest_key(props.get("signal", ""))
        if signal and tile is not None and tile.event and props.get("action") == "fire_signal":
            yield signal, "sends", f"{tile.name} fire_signal", pos
    for area in getattr(level, "areas", []):
        signal = quest_key(area["props"].get("link_id", ""))
        if signal:
            yield signal, "sends", "Area", area["rect"][:2]


def dialogue_signals() -> set:
    """Signals fired by a signal:<id> tag in any dialogue."""
    from components.dialouge_parser import list_dialogues

    found = set()
    for _, filename in list_dialogues():
        try:
            dialogue = load_dialogue(os.path.join(DIALOGUE_DIR, filename))
        except Exception:
            continue
        for passage in dialogue.passages.values():
            for tag in passage.tags:
                if tag.startswith("signal:"):
                    found.add(quest_key(tag[len("signal:") :]))
    return found


def known_signals(level) -> List[Tuple[str, int]]:
    """Signals in use, most used first, for autocomplete: (signal, uses)."""
    counts: Dict[str, int] = {START_SIGNAL: 0}
    for signal, _, _, _ in signal_users(level):
        counts[signal] = counts.get(signal, 0) + 1
    for signal in dialogue_signals():
        counts[signal] = counts.get(signal, 0) + 1
    return sorted(counts.items(), key=lambda item: -item[1])


def flag_users(current=None):
    """Every use of a flag, as (flag, "sets"/"reads", where)."""
    from components.dialouge_parser import list_dialogues

    for level in all_levels(current):
        for pos, props in getattr(level, "properties", {}).items():
            name = f"{level.name or 'this level'} {pos[0]},{pos[1]}"
            if props.get("flag") and props.get("action") == "set_flag":
                yield quest_key(props["flag"]), "sets", name
            for key in ("requires_flag", "requires_not_flag"):
                if props.get(key):
                    yield quest_key(props[key]), "reads", name
    for _, filename in list_dialogues():
        try:
            dialogue = load_dialogue(os.path.join(DIALOGUE_DIR, filename))
        except Exception:
            continue
        for passage in dialogue.passages.values():
            for tag in passage.tags:
                kind, _, value = tag.partition(":")
                if kind in ("flag", "unflag"):
                    yield quest_key(value), "sets", filename
                elif kind in ("if", "ifnot"):
                    yield quest_key(value), "reads", filename


def known_flags(current=None) -> List[Tuple[str, int]]:
    """Flags in use anywhere, most used first, for autocomplete: (flag, uses)."""
    counts: Dict[str, int] = {}
    for flag, _, _ in flag_users(current):
        counts[flag] = counts.get(flag, 0) + 1
    return sorted(counts.items(), key=lambda item: -item[1])


def known_quest_ids(current=None) -> List[Tuple[str, int]]:
    """Quest ids used in any level or dialogue, most used first: (id, uses)."""
    from components.dialouge_parser import list_dialogues

    counts: Dict[str, int] = {}

    def add(value):
        value = quest_key(value or "")
        if value:
            counts[value] = counts.get(value, 0) + 1

    for level in all_levels(current):
        for props in getattr(level, "properties", {}).values():
            for key in ("quest_id", "drop_id", "key_id", "item_id"):
                add(props.get(key))
    for _, filename in list_dialogues():
        try:
            dialogue = load_dialogue(os.path.join(DIALOGUE_DIR, filename))
        except Exception:
            continue
        for passage in dialogue.passages.values():
            for tag in passage.tags:
                kind, _, value = tag.partition(":")
                if kind in ("gives", "requires", "takes"):
                    add(value)
    return sorted(counts.items(), key=lambda item: -item[1])


def find_link_id(level, link_id, skip_pos=None) -> List[Tuple[str, str, Tuple[int, int]]]:
    """Everything in this level that uses this signal, as (label, role, pos)."""
    link_id = quest_key(link_id)
    return [
        (label, role, pos)
        for signal, role, label, pos in signal_users(level)
        if signal == link_id and pos != skip_pos
    ]


Problem = Tuple[str, Optional[Tuple[int, int]]]  # (text, where to jump to)


def link_problems(level) -> List[Problem]:
    """Linkable tiles without an id or action, and signals nothing sends or receives."""
    from tiles import ACTION_FIELDS, OPTIONAL_FIELDS

    problems = []
    linkable = [tile.id for tile in TILES if tile.link]
    for x, y in np.argwhere(np.isin(level.tiles, linkable)):
        pos = (int(x), int(y))
        tile = tile_at(level, pos)
        props = level.properties.get(pos, {})
        if not props.get("link_id") and not props.get("key_id"):  # a locked door needs no button
            problems.append((f"{tile.name} has no link", pos))
        if tile.event:
            action = props.get("action")
            if not action:
                problems.append((f"{tile.name} has no action", pos))
            for key, _ in ACTION_FIELDS.get(action, []):
                if key not in OPTIONAL_FIELDS and not props.get(key):
                    problems.append((f"{action} event has no {key}", pos))

    for area in getattr(level, "areas", []):
        if not area["props"].get("link_id"):
            problems.append(("Area has no link", area["rect"][:2]))

    users: Dict[str, Dict[str, Tuple[int, int]]] = {}  # signal -> role -> first pos
    for signal, role, _, pos in signal_users(level):
        users.setdefault(signal, {}).setdefault(role, pos)
    sent_elsewhere = {START_SIGNAL} | dialogue_signals()
    for signal, roles in users.items():
        first = next(iter(roles.values()))
        if "receives" not in roles:
            problems.append((f"'{signal}' triggers nothing", first))
        if "sends" not in roles and signal not in sent_elsewhere:
            problems.append((f"nothing triggers '{signal}'", first))
    return problems


def sent_signals(level) -> set:
    """Signals something in or around this level can fire."""
    sent = {signal for signal, role, _, _ in signal_users(level) if role == "sends"}
    return sent | {START_SIGNAL} | dialogue_signals()


def reachable(level) -> np.ndarray:
    """Cells the player can reach from the start, walking 4 ways. Doors count
    as open when something can open them: a sent signal or a key."""
    walkable = np.zeros(max(TILE_BY_ID) + 1, dtype=bool)  # per tile id, default state
    for tile in TILES:
        walkable[tile.id] = tile.make(tile.initial_state({}))["walkable"]
    known = level.tiles < len(walkable)
    passable = np.zeros(level.tiles.shape, dtype=bool)
    passable[known] = walkable[level.tiles[known]]
    signals = sent_signals(level)
    for pos, props in level.properties.items():
        tile = tile_at(level, pos)
        if tile is None or not tile.stateful:
            continue
        open_now = tile.make(tile.initial_state(props))["walkable"]
        can_open = tile.on_link is not None and quest_key(props.get("link_id", "")) in signals
        passable[pos] = open_now or can_open or bool(props.get("key_id"))

    seen = np.zeros_like(passable)
    queue = deque([level.player_start])
    seen[level.player_start] = True
    while queue:
        x, y = queue.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < level.width and 0 <= ny < level.height and passable[nx, ny] and not seen[nx, ny]:
                seen[nx, ny] = True
                queue.append((nx, ny))
    return seen


def check_level(level) -> List[Problem]:
    """Everything that looks wrong with a level, for the check report."""
    problems: List[Problem] = []
    if level.stairs_location is None:
        problems.append(("No stairs", None))
    problems += link_problems(level)

    seen = reachable(level)

    def can_reach(pos) -> bool:  # standing on it or right next to it (levers)
        x, y = pos
        return any(
            0 <= nx < level.width and 0 <= ny < level.height and seen[nx, ny]
            for nx, ny in ((x, y), (x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
        )

    stairs = level.stairs_location
    if stairs and not seen[stairs]:
        problems.append(("Stairs can't be reached", stairs))
    for pos, attr in level.entities.items():
        if not isinstance(getattr(entity_factory, attr, None), (Actor, Item)):
            problems.append((f"{attr} no longer exists", pos))
        elif not seen[pos]:
            problems.append((f"{attr} can't be reached", pos))
    for x, y in np.argwhere(level.tiles != TILE_WALL):
        pos = (int(x), int(y))
        tile = tile_at(level, pos)
        if tile is not None and (tile.on_bump or tile.on_step) and not can_reach(pos):
            problems.append((f"{tile.name} can't be reached", pos))

    for pos, props in level.properties.items():
        if props.get("lore") and not os.path.exists(os.path.join(LORE_DIR, props["lore"])):
            problems.append((f"Lore file {props['lore']} is missing", pos))
        if props.get("dialogue") and not os.path.exists(
            os.path.join(DIALOGUE_DIR, props["dialogue"])
        ):
            problems.append((f"Dialogue {props['dialogue']} is missing", pos))
        table = props.get("loot_table")
        if table and table != loot.RANDOM_TABLE:
            try:
                for problem in loot.load(table).problems:
                    problems.append((f"{table}: {problem}", pos))
            except OSError:
                problems.append((f"Loot table {table} is missing", pos))
        if props.get("guaranteed") and not isinstance(
            getattr(entity_factory, props["guaranteed"], None), Item
        ):
            problems.append((f"Guaranteed item {props['guaranteed']} no longer exists", pos))
        for key in ("key_id", "requires_item"):
            if props.get(key):
                produced, _ = find_quest_id(props[key], level)
                if not produced:
                    problems.append((f"Nothing gives '{quest_key(props[key])}' ({key})", pos))

    # flags this level reads that nothing anywhere sets
    users = list(flag_users(level))
    set_somewhere = {flag for flag, role, _ in users if role == "sets"}
    for pos, props in level.properties.items():
        for key in ("requires_flag", "requires_not_flag"):
            flag = quest_key(props.get(key, ""))
            if flag and flag not in set_somewhere:
                problems.append((f"Flag '{flag}' is never set", pos))
    return problems


def normalised(props: dict) -> dict:
    """Copy of props with every id written the way the game compares them."""
    props = dict(props)
    for key in ID_PROPERTIES:
        if key in props:
            props[key] = quest_key(props[key])
    return props


def apply_overrides(actor, props: dict) -> None:
    """Stats and AI set on one placed actor in the editor (hp, power, ...)."""
    fighter = getattr(actor, "fighter", None)
    if fighter is None:
        return

    def number(key) -> Optional[int]:
        try:
            return int(props[key])
        except (KeyError, ValueError):
            return None

    hp = number("hp")
    if hp:
        fighter.base_hp = hp
        fighter._hp = fighter.max_hp
    power = number("power")
    if power is not None:
        fighter.base_power = power
    armor = number("armor")
    if armor is None:
        armor = number("defense")  # levels from before the stat rework
    if armor is not None:
        fighter.base_armor = armor
    xp = number("xp")
    if xp is not None and getattr(actor, "level", None) is not None:
        actor.level.xp_given = xp
    ai_cls = entity_factory.AI_OVERRIDES.get(props.get("ai", ""))
    if ai_cls is not None:
        actor.ai = ai_cls(actor)


def build_game_map(level: CustomLevel, engine: Engine) -> Tuple[GameMap, int]:
    from game_map import GameMap

    player = engine.player
    dungeon = GameMap(engine, level.width, level.height, entities=[player])

    for tile in TILES:
        mask = level.tiles == tile.id
        if tile.id == TILE_WALL or not mask.any():
            continue  # the map starts as all wall
        if not tile.stateful:
            dungeon.tiles[mask] = tile.make()
            continue
        for x, y in np.argwhere(mask):
            pos = (int(x), int(y))
            props = normalised(level.properties.get(pos, {}))
            state = tile.initial_state(props)
            dungeon.tiles[pos] = tile.make(state)
            dungeon.tile_state[pos] = {"tile": tile.id, "state": state, "props": props}

    dungeon.areas = [  # area triggers, see events.enter_areas
        {"rect": tuple(area["rect"]), "props": normalised(area["props"]), "spent": False}
        for area in getattr(level, "areas", [])
    ]

    stairs = level.stairs_location
    dungeon.upstairs_location = stairs if stairs else (-1, -1)

    player.place(*level.player_start, dungeon)

    missing = 0
    for (x, y), attr in level.entities.items():
        prototype = getattr(entity_factory, attr, None)
        if not isinstance(prototype, (Actor, Item)):
            missing += 1
            continue
        spawned = prototype.spawn(dungeon, x, y)
        props = level.properties.get((x, y), {})
        if "name" in props:
            spawned.name = props["name"]
        if is_yes(props.get("invulnerable")):
            spawned.invulnerable = True
        apply_overrides(spawned, props)
        for key in SIGNAL_PROPERTIES:  # on_death / on_pickup, see events.py
            if props.get(key):
                setattr(spawned, key, quest_key(props[key]))
        if "dialogue" in props:
            try:
                spawned.dialogue = load_dialogue(
                    os.path.join(DIALOGUE_DIR, props["dialogue"])
                )
            except Exception:
                spawned.dialogue = None
                engine.message_log.add_message(
                    f"{spawned.name} has nothing to say.", color.impossible
                )
        if "lore" in props:
            try:
                with open(os.path.join(LORE_DIR, props["lore"]), encoding="utf-8") as f:
                    spawned.lore = f.read()
            except OSError:
                spawned.lore = "The pages are blank."

        # a quest item lying on the floor
        if "quest_id" in props:
            spawned.quest_id = quest_key(props["quest_id"])

        # a quest item carried by an enemy or NPC, dropped on death
        if "drop_id" in props and hasattr(spawned, "inventory"):
            drop = copy.deepcopy(entity_factory.quest_item)
            drop.quest_id = quest_key(props["drop_id"])
            drop.name = props.get("drop_name") or props["drop_id"]
            drop.parent = spawned.inventory
            spawned.inventory.items.append(drop)
            spawned.guaranteed_drop = drop

    return dungeon, missing


def new_custom_game(level: CustomLevel) -> Engine:
    import procgen
    from setup_game import create_engine

    engine = create_engine(current_floor=0)
    engine.item_chances = procgen.item_chances
    engine.enemy_chances = procgen.enemy_chances
    engine.game_map, missing = build_game_map(level, engine)

    engine.message_log.add_message("Flesh Tower", color.welcome_text)
    engine.message_log.add_message(f"You awaken in {level.name}")
    engine.game_map.fire(START_SIGNAL)
    engine.update_fov()
    if missing:
        engine.message_log.add_message(
            f"{missing} entities of this level no longer exist", color.impossible
        )
    if level.stairs_location is None:
        engine.message_log.add_message(
            "There are no stairs in this level", color.impossible
        )

    return engine


UNDO_STEPS = 200  # level states kept for undo


def level_state(level: CustomLevel) -> tuple:
    """Everything undo restores: tiles, entities, their properties, areas and
    the player start (not the name; saving is not an edit)."""
    return (
        level.tiles.copy(order="F"),
        copy.deepcopy(level.entities),
        copy.deepcopy(level.properties),
        copy.deepcopy(level.areas),
        level.player_start,
    )


def same_state(level: CustomLevel, state: tuple) -> bool:
    tiles, entities, properties, areas, start = state
    return (
        np.array_equal(level.tiles, tiles)
        and level.entities == entities
        and level.properties == properties
        and level.areas == areas
        and level.player_start == start
    )


def restore_state(level: CustomLevel, state: tuple) -> None:
    tiles, entities, properties, areas, start = copy.deepcopy(state)
    level.tiles[:] = tiles
    level.entities = entities
    level.properties = properties
    level.areas = areas
    level.player_start = start


def event_tile(event) -> Optional[Tuple[int, int]]:
    try:
        tile = event.tile
    except Exception:
        return None
    if tile is None:
        return None
    return int(tile[0]), int(tile[1])


class LevelMenu(input_handlers.BaseEventHandler):
    def __init__(self, main_menu: input_handlers.BaseEventHandler):
        self.main_menu = main_menu
        self.selected = 0
        self.refresh()

    def refresh(self) -> None:
        self.levels = list_levels()
        self.selected = max(0, min(self.selected, len(self.levels) - 1))

    def popup(self, text: str) -> input_handlers.BaseEventHandler:
        return input_handlers.PopupMessage(
            self, text, halved=True, alignment=libtcodpy.CENTER
        )

    def on_render(self, console):
        self.main_menu.on_render(console)
        input_handlers.dim(console)
        width, height = 60, 30
        x, y = input_handlers.draw_box(console, width, height, "Custom Level Select")
        visible_rows = height - 9
        if not self.levels:
            console.print(x + 2, y + 2, "No custom levels", fg=color.impossible)
            console.print(
                x + 2,
                y + 3,
                "Press [N] cave a new Floor into the Tower.",
                fg=color.impossible,
            )
        first = max(0, self.selected - visible_rows + 1)
        for row, (display, _) in enumerate(self.levels[first : first + visible_rows]):
            index = first + row
            text = f" {display}"[: width - 4].ljust(width - 4)
            if index == self.selected:
                console.print(
                    x + 2, y + 2 + row, text, fg=color.menu_title, bg=PANEL_HIGHLIGHT
                )
            else:
                console.print(x + 2, y + 2 + row, text, fg=color.menu_text)

        help_y = y + height - 6
        console.print(x + 2, help_y, "[Enter] play      [E] edit", fg=color.menu_text)
        console.print(
            x + 2, help_y + 1, "[N] new level     [R] rename", fg=color.menu_text
        )
        console.print(
            x + 2, help_y + 2, "[Del] delete      [Esc] back", fg=color.menu_text
        )
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
                return input_handlers.resume_game(new_custom_game(self.load_current()))
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
            return input_handlers.TextPrompt(self, "Rename level", display, self.rename)
        return None

    def rename(self, new_name: str):
        display, filename = self.current()
        problem = input_handlers.check_name(new_name)
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


class LevelEditor(input_handlers.BaseEventHandler):
    def __init__(self, level_menu: LevelMenu, level: CustomLevel):
        self.level_menu = level_menu
        self.level = level
        self.dirty = False

        self.group_index = 0
        self.palette_index = {}
        self.refresh_palette()

        self.brush = BRUSH_TILE
        self.brush_tile = TILE_FLOOR
        self.pick_tile(TILE_FLOOR)
        self.rect_mode = False
        self.rect_anchor: Optional[Tuple[int, int]] = None

        self.mouse: Optional[Tuple[int, int]] = None  # screen tile under mouse
        self.held_button: Optional[int] = None  # 1 left, 3 right

        self.status = "Shape the flesh. [S] saves."
        self.center_camera(*level.player_start)

        # undo: states before each finished change; a change is committed once
        # it is complete (a brush stroke, a rectangle, a closed property menu)
        self.undo_stack: List[tuple] = []
        self.redo_stack: List[tuple] = []
        self.last_state = level_state(level)

        self.pending = None

    def refresh_palette(self) -> None:
        """(Re)builds the palette, e.g. after the entity editor saved."""
        self.palette = {TILE_GROUP: [(tile.id, tile) for tile in TILES]}
        self.palette.update(entity_factory.build_palette())
        self.groups = [group for group, entries in self.palette.items() if entries]
        self.group_index = min(self.group_index, len(self.groups) - 1)
        for group in self.groups:
            index = self.palette_index.get(group, 0)
            self.palette_index[group] = min(index, len(self.palette[group]) - 1)

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
        self.palette_index[self.group] = (self.palette_index[self.group] + step) % len(
            entries
        )
        self.use_palette()

    def use_palette(self) -> None:
        """Brush becomes whatever is selected in the shown palette group."""
        if self.group == TILE_GROUP:
            self.brush = BRUSH_TILE
            self.brush_tile = self.selected_entity()[0]
        else:
            self.brush = BRUSH_ENTITY

    def pick_tile(self, tile_id: int) -> None:
        """Tile brush, with the Tiles palette following along."""
        self.brush, self.brush_tile = BRUSH_TILE, tile_id
        ids = [tile_id_ for tile_id_, _ in self.palette[TILE_GROUP]]
        self.palette_index[TILE_GROUP] = ids.index(tile_id)

    def palette_active(self) -> bool:
        """Is the brush the one selected in the shown palette group?"""
        if self.group == TILE_GROUP:
            return self.brush == BRUSH_TILE
        return self.brush == BRUSH_ENTITY

    def brush_label(self) -> str:
        if self.brush == BRUSH_TILE:
            return TILE_BY_ID[self.brush_tile].name
        if self.brush == BRUSH_START:
            return "Player start"
        if self.brush == BRUSH_SELECT:
            return "Select / edit"
        if self.brush == BRUSH_AREA:
            return "Area trigger"
        return entity_factory.short_name(self.selected_entity()[1])

    def hovered_link(self, pos: Optional[Tuple[int, int]]) -> str:
        """link_id of the linkable tile under the mouse, '' if there is none."""
        if pos is None:
            return ""
        tile = tile_at(self.level, pos)
        if tile is None or not tile.link:
            return ""
        return quest_key(self.level.properties.get(pos, {}).get("link_id", ""))

    def brush_glyph(self) -> Tuple[str, Tuple[int, int, int]]:
        if self.brush == BRUSH_TILE:
            tile = TILE_BY_ID[self.brush_tile]
            return tile.char, tile.color
        if self.brush == BRUSH_START:
            return "@", color.white
        if self.brush == BRUSH_SELECT:
            return "?", color.white
        if self.brush == BRUSH_AREA:
            return "[", (230, 200, 120)
        prototype = self.selected_entity()[1]
        return prototype.char, prototype.color

    def paint(self, x: int, y: int) -> None:
        level = self.level
        tile = tile_at(level, (x, y))
        if self.brush == BRUSH_SELECT:
            if tile is not None and tile.properties:
                # fields may depend on the values, e.g. the action of an event marker
                self.pending = input_handlers.PropertyMenu(self, (x, y), tile.fields_for)
                return
            attr = level.entities.get((x, y))
            fields = entity_factory.editable_properties(attr) if attr else []
            area = level.area_at((x, y))
            if fields:
                self.pending = input_handlers.PropertyMenu(self, (x, y), fields)
            elif area is not None:
                self.pending = self.area_menu(area)
            else:
                self.status = "Nothing to edit here"
            return
        if self.brush == BRUSH_TILE:
            brush = TILE_BY_ID[self.brush_tile]
            if brush.solid:
                if (x, y) == level.player_start:
                    self.status = "Can't build on the start"
                    return
                if level.entities.pop((x, y), None) is not None:
                    level.properties.pop((x, y), None)
            if tile is not None and tile.properties and tile.id != brush.id:
                level.properties.pop(
                    (x, y), None
                )  # e.g. floor over a door drops its link
            if brush.unique:
                for ox, oy in np.argwhere(level.tiles == brush.id):
                    if (ox, oy) != (x, y):
                        level.tiles[ox, oy] = TILE_FLOOR
                        level.properties.pop((int(ox), int(oy)), None)
                        self.status = f"{brush.name} moved (one per level)"
            if level.tiles[x, y] != brush.id:
                level.tiles[x, y] = brush.id
                self.dirty = True
        elif self.brush == BRUSH_START:
            if level.player_start != (x, y):
                level.entities.pop((x, y), None)
                level.player_start = (x, y)
                if tile is None or tile.solid:
                    level.tiles[x, y] = TILE_FLOOR
                    level.properties.pop((x, y), None)
                self.dirty = True
        else:
            if (x, y) == level.player_start:
                self.status = "The player stands there"
                return
            attr = self.selected_entity()[0]
            if level.entities.get((x, y)) != attr:
                level.entities[(x, y)] = attr
                level.properties.pop((x, y), None)
                if tile is None or tile.solid:
                    level.tiles[x, y] = TILE_FLOOR
                self.dirty = True

    def erase(self, x: int, y: int) -> None:
        level = self.level
        if (x, y) in level.entities:
            del level.entities[(x, y)]
            level.properties.pop((x, y), None)
            self.dirty = True
        elif (x, y) == level.player_start:
            self.status = "Move the start with [4]"
        elif level.tiles[x, y] != TILE_WALL:
            level.properties.pop((x, y), None)
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
                    self.brush == BRUSH_TILE and TILE_BY_ID[self.brush_tile].unique
                ):
                    self.paint(b[0], b[1])
                    return
                else:
                    self.paint(x, y)

    def apply_at_mouse(self) -> None:
        pos = self.map_pos()
        if pos is None or self.held_button is None or self.rect_mode or self.brush == BRUSH_AREA:
            return
        if self.held_button == 1:
            self.paint(*pos)
        elif self.held_button == 3:
            self.erase(*pos)

    def ask_save(self, then_leave: bool = False):
        def submit(name: str):
            problem = input_handlers.check_name(name)
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

        prompt = input_handlers.TextPrompt(
            self, "Save level as", self.level.name, submit
        )
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
        problems = check_level(self.level)
        if problems:
            self.status += f". {problems[0][0]}"
            if len(problems) > 1:
                self.status += f" (+{len(problems) - 1} more, [V] shows all)"
        self.level_menu.refresh()
        if then_leave:
            return self.leave()
        return self

    def leave(self):
        self.level_menu.refresh()
        return self.level_menu

    def check_report(self):
        """[V]: every problem of the level, Enter jumps to it."""
        problems = check_level(self.level)
        if not problems:
            self.status = "No problems found"
            return None

        def jump(pos):
            if pos is not None:
                self.center_camera(*pos)
                self.status = f"Jumped to {pos[0]},{pos[1]}"
            return self

        items = [
            (f"{text}" + (f"  ({pos[0]},{pos[1]})" if pos else ""), pos)
            for text, pos in problems
        ]
        return input_handlers.ListPicker(self, f"Check level: {len(problems)} problems", items, jump)

    def ev_quit(self, event):
        if self.dirty:
            name = self.level.name or "autosave"
            self.level.name = name
            try:
                save_level(self.level)
                self.dirty = False  # main.save_game would write it again otherwise
                print(f"Unsaved level written to {level_file_name(name)}")
            except Exception:
                traceback.print_exc()
        raise SystemExit()

    def commit_history(self) -> None:
        """Records the level as it was before the last finished change. Called
        on every input; while a mouse stroke is held it waits for the release,
        so one stroke is one undo step."""
        if self.held_button is not None:
            return
        if same_state(self.level, self.last_state):
            return
        self.undo_stack.append(self.last_state)
        del self.undo_stack[:-UNDO_STEPS]
        self.redo_stack.clear()
        self.last_state = level_state(self.level)

    def undo(self) -> None:
        self.commit_history()
        if not self.undo_stack:
            self.status = "Nothing to undo"
            return
        self.redo_stack.append(self.last_state)
        self.last_state = self.undo_stack.pop()
        restore_state(self.level, self.last_state)
        self.dirty = True
        self.status = f"Undo ({len(self.undo_stack)} more)"

    def redo(self) -> None:
        self.commit_history()
        if not self.redo_stack:
            self.status = "Nothing to redo"
            return
        self.undo_stack.append(self.last_state)
        self.last_state = self.redo_stack.pop()
        restore_state(self.level, self.last_state)
        self.dirty = True
        self.status = f"Redo ({len(self.redo_stack)} more)"

    def ev_mousemotion(self, event):
        self.commit_history()
        self.mouse = event_tile(event)
        self.apply_at_mouse()

    def ev_mousebuttondown(self, event):
        self.commit_history()
        tile = event_tile(event)
        if tile is not None:
            self.mouse = tile
        self.held_button = int(event.button)
        if self.brush == BRUSH_AREA:
            pos = self.map_pos()
            if self.held_button == 3 and pos is not None:
                self.delete_area(pos)
                self.held_button = None
            else:
                self.rect_anchor = pos
        elif self.rect_mode:
            self.rect_anchor = self.map_pos()
        else:
            self.apply_at_mouse()
        if self.pending is not None:
            handler, self.pending = self.pending, None
            self.held_button = None
            return handler

    def ev_mousebuttonup(self, event):
        handler = None
        if self.rect_anchor is not None:
            end = self.map_pos()
            if end is not None and self.brush == BRUSH_AREA:
                handler = self.add_area(self.rect_anchor, end)
            elif end is not None and self.rect_mode:
                self.fill_rect(self.rect_anchor, end, erase=self.held_button == 3)
        self.rect_anchor = None
        self.held_button = None
        self.commit_history()
        return handler

    def area_menu(self, area: dict):
        from tiles import AREA_FIELDS

        return input_handlers.PropertyMenu(self, None, AREA_FIELDS, values=area["props"])

    def add_area(self, a: Tuple[int, int], b: Tuple[int, int]):
        x1, x2 = sorted((a[0], b[0]))
        y1, y2 = sorted((a[1], b[1]))
        area = {"rect": (x1, y1, x2, y2), "props": {}}
        self.level.areas.append(area)
        self.dirty = True
        self.status = "Area added, give it a link_id"
        return self.area_menu(area)

    def delete_area(self, pos: Tuple[int, int]) -> None:
        area = self.level.area_at(pos)
        if area is None:
            self.status = "No area here"
            return
        self.level.areas.remove(area)
        self.dirty = True
        self.status = "Area removed"

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
        self.commit_history()

        if key == k.Z and mod & SHIFT and mod & tcod.event.Modifier.CTRL:
            self.redo()  # Ctrl+Shift+Z
            return None
        if key == k.Z:
            self.undo()  # Z or Ctrl+Z
            return None
        if key == k.Y:
            self.redo()  # Y or Ctrl+Y
            return None

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
            self.pick_tile(TILE_WALL)
        elif key == k.N2:
            self.pick_tile(TILE_FLOOR)
        elif key == k.N3:
            self.pick_tile(TILE_STAIRS)
        elif key == k.N4:
            self.brush = BRUSH_START
        elif key == k.N5:
            self.use_palette()
        elif key == k.N6:
            self.brush = BRUSH_SELECT
        elif key == k.N7:
            self.brush = BRUSH_AREA
        elif key == k.TAB:
            self.group_index = (self.group_index + 1) % len(self.groups)
            self.use_palette()
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
        elif key == k.V:
            return self.check_report()
        elif key == k.E:
            import entity_editor

            return entity_editor.entity_list(self)
        elif key == k.ESCAPE:
            if self.dirty:
                return input_handlers.PopupToConfirm(
                    self, "Leave without saving?", self.leave
                )
            return self.leave()
        self.clamp_camera()
        self.apply_at_mouse()
        return None

    def on_render(self, console):
        level = self.level
        cx, cy = self.cam_x, self.cam_y
        view = level.tiles[cx : cx + VIEW_WIDTH, cy : cy + VIEW_HEIGHT]
        console.rgb[0 : view.shape[0], 0 : view.shape[1]] = TILE_GRAPHICS[view]

        for area in level.areas:  # tint area triggers
            x1, y1, x2, y2 = area["rect"]
            sx1, sx2 = max(x1 - cx, 0), min(x2 - cx + 1, VIEW_WIDTH)
            sy1, sy2 = max(y1 - cy, 0), min(y2 - cy + 1, VIEW_HEIGHT)
            if sx1 < sx2 and sy1 < sy2:
                console.rgb["bg"][sx1:sx2, sy1:sy2] = AREA_BG

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
        link_id = self.hovered_link(pos)
        if link_id:
            # show everything this button/door is linked with
            for _, _, (lx, ly) in find_link_id(level, link_id):
                sx, sy = lx - cx, ly - cy
                if 0 <= sx < VIEW_WIDTH and 0 <= sy < VIEW_HEIGHT:
                    console.rgb["bg"][sx, sy] = LINK_BG
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
        console.draw_frame(
            x=x,
            y=0,
            width=w,
            height=console.height,
            title="Editor",
            clear=True,
            fg=color.white,
            bg=color.black,
        )
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
            else:
                tile = tile_at(self.level, pos)
                if tile is not None and tile.link:
                    link_id = self.hovered_link(pos) or "-"
                    console.print(
                        x + 1, 7, f"link: {link_id}"[:inner], fg=color.impossible
                    )
                if tile is not None and tile.event:
                    action = self.level.properties.get(pos, {}).get("action", "-")
                    console.print(x + 1, 8, f"do: {action}"[:inner], fg=color.impossible)
            area = self.level.area_at(pos)
            hovered = tile_at(self.level, pos)
            if area is not None and not (hovered is not None and hovered.event):  # "do:" uses line 8
                area_link = area["props"].get("link_id") or "-"
                console.print(x + 1, 8, f"area: {area_link}"[:inner], fg=color.impossible)

        console.print(x + 1, 9, f"<{self.group}> Tab"[:inner], fg=color.menu_title)
        entries = self.palette[self.group]
        current = self.palette_index[self.group]
        first = max(0, min(current - PALETTE_ROWS // 2, len(entries) - PALETTE_ROWS))
        for row, (attr, prototype) in enumerate(entries[first : first + PALETTE_ROWS]):
            index = first + row
            y = 10 + row
            label = f" {entity_factory.short_name(prototype)}"[: inner - 1].ljust(
                inner - 1
            )
            selected = index == current
            bg = (
                PANEL_HIGHLIGHT
                if selected and self.palette_active()
                else ((40, 40, 40) if selected else color.black)
            )
            console.print(x + 1, y, prototype.char, fg=prototype.color, bg=bg)
            console.print(x + 2, y, label, fg=color.white, bg=bg)

        help_lines = [
            "1 wall  ",
            "2 floor",
            "3 stairs ",
            "4 start",
            "5 palette [ ] pick",
            "Tab next palette",
            "6 select / edit",
            "7 area trigger",
            "LMB draw RMB erase",
            "R rectangle mode",
            "Arrows pan (Shift)",
            "Wheel scroll/pick",
            "C center on start",
            "V check level",
            "E edit entities",
            "Z undo  Y redo",
            "S save  Esc back",
        ]
        help_y = 11 + PALETTE_ROWS + 1
        for i, line in enumerate(help_lines):
            console.print(x + 1, help_y + i, line[:inner], fg=color.impossible)

        status_y = console.height - 4
        for i in range(0, min(len(self.status), inner * 3), inner):
            console.print(
                x + 1,
                status_y + i // inner,
                self.status[i : i + inner],
                fg=color.menu_title,
            )
