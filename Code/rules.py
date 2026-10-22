"""The level-design vocabulary: conditions and actions, shared by event
markers, lockable tiles, area triggers and dialogue tags.

Conditions (editor fields and dialogue tags, same names):
    if:<flag>          the flag is set
    ifnot:<flag>       the flag is not set
    requires:<item>    the player carries the quest item
Doors and chests also have consume (yes/no): the required item is taken.

Actions (event marker "action" field, or a dialogue tag <action>:<value>):
    message  lore  spawn  teleport  gives  takes  organs  signal
    flag  unflag  die  end_level
An event marker fills an action's fields in the editor; a dialogue tag gives
its first field as the value (spaces in a message written as _).

Names used everywhere:
    signal     the signal a tile or area sends or listens to
    target     the signal the signal action fires
    quest      the quest id an item is
    requires / gives / takes / drop   refer to an item (a data id or quest id)

Older names in level files, savegames and dialogues still work: levels and
saves are upgraded when loaded (upgrade_props), old dialogue tags are read
through TAG_ALIASES and the V check points them out.
"""
from __future__ import annotations

import copy
import os
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from components.dialouge_parser import quest_key

# --- conditions ---------------------------------------------------------------

CONDITION_FIELDS: List[Tuple[str, str]] = [
    ("if", "flag"),
    ("ifnot", "flag"),
    ("requires", "quest"),
]
CONDITION_KEYS = tuple(key for key, _ in CONDITION_FIELDS)
LOCK_FIELDS = CONDITION_FIELDS + [("consume", "bool")]  # doors and chests


def conditions_from_props(props: dict) -> List[Tuple[str, str]]:
    return [(key, props[key]) for key in CONDITION_KEYS if props.get(key)]


def conditions_from_tags(tags: Iterable[str]) -> List[Tuple[str, str]]:
    found = []
    for tag in tags:
        name, _, value = tag.partition(":")
        if name in CONDITION_KEYS and value:
            found.append((name, quest_key(value)))
    return found


def carried_quest_item(player, quest_id: str):
    for item in player.inventory.items:
        if getattr(item, "quest_id", None) == quest_id:
            return item
    return None


def failed_condition(engine, conditions) -> Optional[Tuple[str, str]]:
    """The first condition that does not hold, or None when all hold."""
    from events import get_flags

    flags = get_flags(engine)
    for kind, value in conditions:
        if kind == "if" and value not in flags:
            return kind, value
        if kind == "ifnot" and value in flags:
            return kind, value
        if kind == "requires" and carried_quest_item(engine.player, value) is None:
            return kind, value
    return None


def conditions_met(engine, conditions) -> bool:
    return failed_condition(engine, conditions) is None


def props_met(engine, props: dict) -> bool:
    return conditions_met(engine, conditions_from_props(props))


# --- items ----------------------------------------------------------------------


def make_quest_item(quest_id: str, name: str = ""):
    """A quest item with this id: the one place quest items are made."""
    import entity_factory

    item = copy.deepcopy(entity_factory.quest_item)
    item.quest_id = quest_key(quest_id)
    item.name = name or item.quest_id.replace("_", " ").title()
    return item


# data ids renamed to snake_case; levels, loot tables and tags may still say the old ones
OLD_ENTITY_IDS = {
    "genericNPC": "npc",
    "genericLoreItem": "lore_note",
    "healing_scrollI": "healing_scroll_1",
    "healing_scrollII": "healing_scroll_2",
    "healing_scrollIII": "healing_scroll_3",
}


def entity_id(value: str) -> str:
    return OLD_ENTITY_IDS.get(value or "", value or "")


def item_prototype(item_id: str):
    """The data entity with this id if it is an item, else None."""
    import entity_factory
    from entity import Item

    prototype = getattr(entity_factory, entity_id(item_id), None)
    return prototype if isinstance(prototype, Item) else None


def give_to_player(engine, item) -> None:
    """Puts an item into the player's inventory, or on the floor if it is full."""
    import color

    player = engine.player
    if len(player.inventory.items) < player.inventory.capacity:
        item.parent = player.inventory
        player.inventory.items.append(item)
        engine.message_log.add_message(f"You receive the {item.name}.", color.menu_title)
    else:
        item.place(player.x, player.y, engine.game_map)
        engine.message_log.add_message(
            f"Your hands are full. The {item.name} falls to the floor.", color.menu_title
        )


# --- actions --------------------------------------------------------------------


@dataclass
class Action:
    name: str
    fields: List[Tuple[str, str]]  # editor fields of an event marker, first = tag value
    run: Callable  # (ctx, props) -> None
    optional: Tuple[str, ...] = ()  # fields that may stay empty
    in_dialogue: bool = True
    help: str = ""

    @property
    def main(self) -> Optional[str]:
        return self.fields[0][0] if self.fields else None


def free_spot_near(game_map, pos, include_pos: bool = True):
    """pos if free, else the nearest free walkable tile around it."""
    x0, y0 = pos
    for radius in range(0 if include_pos else 1, 4):
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                x, y = x0 + dx, y0 + dy
                if max(abs(dx), abs(dy)) != radius or not game_map.in_bounds(x, y):
                    continue
                if game_map.tiles["walkable"][x, y] and not game_map.get_blocking_entity_at_location(x, y):
                    return x, y
    return None


def act_message(ctx, props) -> None:
    import color

    for line in props.get("text", "").replace("_", " ").splitlines():
        if line.strip():
            ctx.engine.message_log.add_message(line, color.menu_title)


def act_lore(ctx, props) -> None:
    from components.settings import LORE_DIR

    filename = props.get("lore", "")
    if filename and not filename.endswith(".txt"):
        filename += ".txt"
    try:
        with open(os.path.join(LORE_DIR, filename), encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return
    # shown by input_handlers.resume_game; plain data so saving still works
    ctx.engine.pending_screen = SimpleNamespace(
        name=filename[: -len(".txt")].replace("_", " "), lore=text
    )


def act_spawn(ctx, props) -> None:
    import entity_factory
    from entity import Actor, Item

    prototype = getattr(entity_factory, entity_id(props.get("entity", "")), None)
    if not isinstance(prototype, (Actor, Item)):
        return
    if ctx.npc is not None:  # from dialogue: next to the speaker
        spot = free_spot_near(ctx.game_map, ctx.pos, include_pos=False)
    elif prototype.blocks_movement and ctx.game_map.get_blocking_entity_at_location(*ctx.pos):
        spot = None  # something already stands on the marker
    else:
        spot = ctx.pos
    if spot is not None:
        prototype.spawn(ctx.game_map, *spot)


def act_teleport(ctx, props) -> None:
    if ctx.game_map.get_blocking_entity_at_location(*ctx.pos):
        return
    ctx.engine.player.place(*ctx.pos, ctx.game_map)
    ctx.engine.update_fov()


def make_item(value: str, name: str = ""):
    """A copy of the data item with this id, else a quest item with this id."""
    prototype = item_prototype(value)
    if prototype is None:
        return make_quest_item(value, name)
    item = copy.deepcopy(prototype)
    if name:
        item.name = name
    return item


def act_gives(ctx, props) -> None:
    if props.get("item"):
        give_to_player(ctx.engine, make_item(props["item"], props.get("name", "")))


def act_takes(ctx, props) -> None:
    item = carried_quest_item(ctx.engine.player, quest_key(props.get("item", "")))
    if item is not None:
        ctx.engine.player.inventory.items.remove(item)
        ctx.engine.message_log.add_message(f"You hand over the {item.name}.")


def act_organs(ctx, props) -> None:
    import color

    try:
        organs = int(props.get("amount", 0))
    except (TypeError, ValueError):
        return
    ctx.engine.player.currency += organs
    if organs >= 0:
        ctx.engine.message_log.add_message(f"You receive {organs} organs.", color.menu_title)
    else:
        ctx.engine.message_log.add_message(f"You pay {-organs} organs.")


def act_signal(ctx, props) -> None:
    from events import fire

    fire(ctx.game_map, props.get("target", ""), ctx.depth + 1)


def act_flag(ctx, props) -> None:
    from events import get_flags

    if props.get("flag"):
        get_flags(ctx.engine).add(quest_key(props["flag"]))


def act_unflag(ctx, props) -> None:
    from events import get_flags

    if props.get("flag"):
        get_flags(ctx.engine).discard(quest_key(props["flag"]))


def act_die(ctx, props) -> None:
    """The speaker (dialogue) or whatever stands on the marker dies as if
    killed: corpse, xp, drops, on_death. Works on invulnerable NPCs too."""
    target = ctx.npc
    if target is None:
        target = ctx.game_map.get_actor_at_location(*ctx.pos)
    if target is not None and target is not ctx.engine.player and target.is_alive:
        target.fighter.die()


def act_end_level(ctx, props) -> None:
    import color

    ctx.engine.message_log.add_message("The tower shifts around you.", color.ascend)
    ctx.engine.game_world.generate_floor()
    ctx.engine.update_fov()


ACTIONS: Dict[str, Action] = {
    action.name: action
    for action in [
        Action("message", [("text", "long_text")], act_message, help="show text in the log"),
        Action("lore", [("lore", "lore")], act_lore, help="open a lore page"),
        Action("spawn", [("entity", "entity")], act_spawn, help="create a monster or item"),
        Action("teleport", [], act_teleport, in_dialogue=False, help="move the player to the marker"),
        Action("gives", [("item", "gives"), ("name", "text")], act_gives, optional=("name",),
               help="give an item (data id) or a quest item"),
        Action("takes", [("item", "quest")], act_takes, help="take a quest item"),
        Action("organs", [("amount", "signed_int")], act_organs, help="give (or with - take) organs"),
        Action("signal", [("target", "signal")], act_signal, help="fire another signal"),
        Action("flag", [("flag", "flag")], act_flag, help="set a flag"),
        Action("unflag", [("flag", "flag")], act_unflag, help="clear a flag"),
        Action("die", [], act_die, help="kill the speaker / whatever stands on the marker"),
        Action("end_level", [], act_end_level, help="go to the next level"),
    ]
}


def run_action(name: str, ctx, props: dict) -> bool:
    action = ACTIONS.get(name)
    if action is None:
        return False
    action.run(ctx, props)
    return True


def context(engine, game_map, pos, npc=None, depth: int = 0) -> SimpleNamespace:
    """Where an action happens: the marker's tile, or the speaking NPC."""
    return SimpleNamespace(engine=engine, game_map=game_map, pos=pos, npc=npc, depth=depth)


# --- dialogue tags ----------------------------------------------------------------

TAG_ALIASES = {"item": "gives"}  # old dialogue tag -> action
NON_ACTION_TAGS = ("start",) + CONDITION_KEYS


def tag_actions(tags: Iterable[str]) -> List[Tuple[str, dict]]:
    """(action, props) for every action tag, in the order written."""
    found = []
    for tag in tags:
        name, _, value = tag.partition(":")
        name = TAG_ALIASES.get(name, name)
        action = ACTIONS.get(name)
        if action is None or not action.in_dialogue:
            continue
        props = {action.main: value} if action.main else {}
        found.append((name, props))
    return found


def old_tags(tags: Iterable[str]) -> List[Tuple[str, str]]:
    """(old, new) for tags written with an old name, for the V check."""
    return [
        (tag, TAG_ALIASES[tag.partition(":")[0]] + ":" + tag.partition(":")[2])
        for tag in tags
        if tag.partition(":")[0] in TAG_ALIASES
    ]


# --- upgrading older level files and savegames ----------------------------------

# 0: before the shared rules, 1: shared rules with link_id, 2: names unified
RULES_VERSION = 2

OLD_PROP_NAMES = {
    "requires_flag": "if",
    "requires_not_flag": "ifnot",
    "requires_item": "requires",
    "consume_key": "consume",
}
OLD_ACTIONS = {"give_item": "gives", "fire_signal": "signal"}  # set_flag: see below


def upgrade_props(props: dict, version: int = 0) -> dict:
    """Copy of props written with today's names. version: the rules version
    the props were saved with (each step runs once)."""
    props = dict(props)
    if version < 1:
        for old, new in OLD_PROP_NAMES.items():
            if old in props:
                value = props.pop(old)
                props.setdefault(new, value)
        if "key_id" in props:  # door / chest key: now an ordinary requires
            key = props.pop("key_id")
            if props.get("requires") and props["requires"] != key:
                print(f"Level upgrade: key {key} replaces requires {props['requires']}")
            props["requires"] = key
        action = props.get("action")
        if action in OLD_ACTIONS:
            props["action"] = OLD_ACTIONS[action]
        if action == "give_item":
            if "item_id" in props:
                props["item"] = props.pop("item_id")
            if "item_name" in props:
                props["name"] = props.pop("item_name")
        if action == "set_flag":
            props["action"] = "unflag" if props.pop("value", "on") == "off" else "flag"
    if version < 2:
        if props.get("action") == "signal" and "signal" in props:
            props["target"] = props.pop("signal")  # the signal it fires
        if "link_id" in props:
            props["signal"] = props.pop("link_id")  # the signal it sends or listens to
        if "guaranteed" in props:
            props["gives"] = props.pop("guaranteed")
        if "quest_id" in props:
            props["quest"] = props.pop("quest_id")
        if "drop_id" in props:
            props["drop"] = props.pop("drop_id")
        for key in ("entity", "item", "gives"):
            if key in props:
                props[key] = entity_id(props[key])
    return props
