"""Signals: triggers fire a signal, receivers react to it.

A signal is a link_id. It is fired by
  - tiles that send: levers when bumped, plates when stepped on
  - entity props on_death / on_pickup (set in the level editor)
  - the dialogue tag signal:<id>
  - the level itself when it starts (START_SIGNAL)
  - an event marker with the action fire_signal

Receivers are tiles with that link_id: doors switch state (TileDef.on_link),
event markers run their action (ACTIONS below, fields in tiles.ACTION_FIELDS).
"""
from __future__ import annotations

import copy
import os
from types import SimpleNamespace
from typing import TYPE_CHECKING, Tuple

import color
from components.dialouge_parser import quest_key
from components.settings import LORE_DIR
from tiles import TILE_BY_ID, is_yes

if TYPE_CHECKING:
    from engine import Engine
    from game_map import GameMap

MAX_DEPTH = 8  # how often signals may fire each other in a row


def fire(game_map: GameMap, signal: str, depth: int = 0) -> int:
    """Fires a signal on this map. Returns how many receivers reacted."""
    signal = quest_key(signal or "")
    if not signal:
        return 0
    if depth > MAX_DEPTH:
        print(f"Signal '{signal}' chained more than {MAX_DEPTH} times, stopped")
        return 0

    engine = game_map.engine
    reacted = 0
    for pos, info in list(getattr(game_map, "tile_state", {}).items()):
        if engine.game_map is not game_map:
            break  # an end_level action replaced the map
        if info["props"].get("link_id") != signal:
            continue
        tile = TILE_BY_ID[info["tile"]]
        if tile.on_link is not None:
            reacted += switch(game_map, pos, info)
        elif tile.event:
            action = ACTIONS.get(info["props"].get("action", ""))
            if action is not None:
                action(engine, game_map, pos, info["props"], depth)
                reacted += 1
    return reacted


def switch(game_map: GameMap, pos: Tuple[int, int], info: dict) -> int:
    """Changes a receiving tile's state, e.g. opens or closes a door."""
    tile = TILE_BY_ID[info["tile"]]
    state = tile.on_link(info["state"], info["props"])
    if state == info["state"]:
        return 0
    # never close something on whatever stands in it
    if not tile.make(state)["walkable"] and any(
        e.x == pos[0] and e.y == pos[1] for e in game_map.entities
    ):
        return 0
    game_map.set_tile_state(pos, state)
    return 1


def on_step(game_map: GameMap, pos: Tuple[int, int]) -> None:
    """The player stepped on pos: plates fire their signal."""
    info = getattr(game_map, "tile_state", {}).get(pos)
    if info is None or not TILE_BY_ID[info["tile"]].on_step or info.get("spent"):
        return
    props = info["props"]
    if not is_yes(props.get("repeat")):
        info["spent"] = True
        if info["state"] == "armed":
            game_map.set_tile_state(pos, "spent")
    if info["state"] != "hidden":
        game_map.engine.message_log.add_message("Something clicks beneath your feet.")
    fire(game_map, props.get("link_id", ""))


# --- actions of event markers: (engine, game_map, marker pos, props, depth) ---


def act_message(engine: Engine, game_map, pos, props, depth) -> None:
    for line in props.get("text", "").splitlines():
        if line.strip():
            engine.message_log.add_message(line, color.menu_title)


def act_lore(engine: Engine, game_map, pos, props, depth) -> None:
    filename = props.get("lore", "")
    try:
        with open(os.path.join(LORE_DIR, filename), encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return
    # shown by input_handlers.resume_game after the turn; plain data so saving still works
    engine.pending_screen = SimpleNamespace(
        name=filename[: -len(".txt")].replace("_", " "), lore=text
    )


def act_spawn(engine: Engine, game_map, pos, props, depth) -> None:
    import entity_factory
    from entity import Actor, Item

    prototype = getattr(entity_factory, props.get("entity", ""), None)
    if not isinstance(prototype, (Actor, Item)):
        return
    if prototype.blocks_movement and game_map.get_blocking_entity_at_location(*pos):
        return  # something already stands there
    prototype.spawn(game_map, *pos)


def act_teleport(engine: Engine, game_map, pos, props, depth) -> None:
    if game_map.get_blocking_entity_at_location(*pos):
        return
    engine.player.place(*pos, game_map)
    engine.update_fov()


def act_give_item(engine: Engine, game_map, pos, props, depth) -> None:
    import entity_factory
    from input_handlers import give_item

    quest_id = props.get("item_id", "")
    if not quest_id:
        return
    item = copy.deepcopy(entity_factory.quest_item)
    item.quest_id = quest_id
    item.name = props.get("item_name") or quest_id.replace("_", " ").title()
    give_item(engine, item)


def act_fire_signal(engine: Engine, game_map, pos, props, depth) -> None:
    fire(game_map, props.get("signal", ""), depth + 1)


def act_end_level(engine: Engine, game_map, pos, props, depth) -> None:
    engine.message_log.add_message("The tower shifts around you.", color.ascend)
    engine.game_world.generate_floor()
    engine.update_fov()


ACTIONS = {
    "message": act_message,
    "lore": act_lore,
    "spawn": act_spawn,
    "teleport": act_teleport,
    "give_item": act_give_item,
    "fire_signal": act_fire_signal,
    "end_level": act_end_level,
}
