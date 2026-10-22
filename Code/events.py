"""Signals: triggers fire a signal, receivers react to it.

A signal is a name in a tile or area's "signal" field. It is fired by
  - tiles that send: levers when bumped, chests when opened
  - area triggers when the player walks in
  - entity props on_death / on_pickup (set in the level editor)
  - the action signal (event markers, dialogue tag signal:<id>)
  - the level itself when it starts (START_SIGNAL)

Receivers are tiles with that signal: doors switch state (TileDef.on_link),
event markers run their action (rules.ACTIONS).

Event markers, levers, chests and areas only react when their conditions hold
(rules.py: if / ifnot / requires). Event markers can wait some turns (delay).
Flags live on the engine (get_flags); the actions flag / unflag change them.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Tuple

import rules
from components.dialouge_parser import quest_key
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
        if info["props"].get("signal") != signal:
            continue
        tile = TILE_BY_ID[info["tile"]]
        if tile.on_link is not None:
            reacted += switch(game_map, pos, info)
        elif tile.event and rules.props_met(engine, info["props"]):
            delay = number(info["props"].get("delay"))
            if delay > 0:
                pending_events(game_map).append([delay, pos])
            else:
                run_event(game_map, pos, info, depth)
            reacted += 1
    return reacted


def run_event(game_map: GameMap, pos, info: dict, depth: int = 0) -> None:
    ctx = rules.context(game_map.engine, game_map, pos, depth=depth)
    rules.run_action(info["props"].get("action", ""), ctx, info["props"])


def tick(game_map: GameMap) -> None:
    """Once per turn: runs delayed events that are due."""
    pending = getattr(game_map, "pending_events", None)
    if not pending:
        return
    due = []
    for entry in pending:
        entry[0] -= 1
        if entry[0] <= 0:
            due.append(entry)
    game_map.pending_events = [entry for entry in pending if entry[0] > 0]
    for _, pos in due:
        if game_map.engine.game_map is not game_map:
            break  # an end_level action replaced the map
        info = game_map.tile_state.get(pos)
        if info is not None:
            run_event(game_map, pos, info)


def pending_events(game_map: GameMap) -> list:
    """[[turns left, marker pos]], kept on the map so it is saved with the game."""
    if not hasattr(game_map, "pending_events"):
        game_map.pending_events = []
    return game_map.pending_events


def number(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def get_flags(engine: Engine) -> set:
    """Flags set by events and dialogue, kept on the engine so they last
    across levels and are saved with the game."""
    if not hasattr(engine, "flags"):
        engine.flags = set()
    return engine.flags


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


def enter_areas(game_map: GameMap, pos: Tuple[int, int], previous: Tuple[int, int]) -> None:
    """The player moved from previous to pos: areas just walked into fire."""

    def inside(rect, point) -> bool:
        x1, y1, x2, y2 = rect
        return x1 <= point[0] <= x2 and y1 <= point[1] <= y2

    for area in getattr(game_map, "areas", []):
        if area["spent"] or not inside(area["rect"], pos) or inside(area["rect"], previous):
            continue
        props = area["props"]
        if not rules.props_met(game_map.engine, props):
            continue
        if not is_yes(props.get("repeat")):
            area["spent"] = True
        fire(game_map, props.get("signal", ""))
        if game_map.engine.game_map is not game_map:
            return  # an end_level action replaced the map


def on_step(game_map: GameMap, pos: Tuple[int, int], previous: Tuple[int, int]) -> None:
    """The player stepped from previous onto pos: areas walked into fire."""
    enter_areas(game_map, pos, previous)
