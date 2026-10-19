"""Every item and actor the game knows.

Everything comes from the data files in Data/ (see entity_data.py) and becomes
an attribute of this module under its id, so entity_factory.health_potion and
`from entity_factory import rat` work. The player is the "player" entry of
Data/actors.json; it is editable but never placed or spawned.
"""
from components.ai import (
    HostileEnemy,
    HostileCaster,
    Vendor,
)
from components.effects import DefaultEffect, LogBook
from components.equipment import Equipment
from components.fighter import Fighter
from components.inventory import Inventory
from components.level import Level
from components.spells import SpellBook
from components import stats
from entity import Actor, Item
import entity_data

from typing import Dict, List, Tuple

EDITABLE_PROPERTIES = {
    "genericNPC": [("name", "text"), ("dialogue", "dialogue"), ("invulnerable", "bool")],
    "genericLoreItem": [("name", "text"), ("lore", "lore")],
    "quest_item": [("name", "text"), ("quest_id", "quest_id")],
}

# AIs a placed actor can be switched to in the level editor
AI_OVERRIDES = {
    "hostile": HostileEnemy,
    "caster": HostileCaster,
    "neutral": Vendor,  # stands still, never attacks
}

PLAYER_ID = "player"

# entity id -> data file category ("actors", "items", "equipment"), in load order
CATEGORY: Dict[str, str] = {}


def short_name(entity) -> str:
    return entity.name


def build_palette() -> Dict[str, List[Tuple[str, object]]]:
    """Level editor palette groups, one per data file."""
    palette = {group: [] for group in entity_data.CATEGORIES.values()}
    for entity_id, category in CATEGORY.items():
        if entity_id == PLAYER_ID:
            continue
        palette[entity_data.CATEGORIES[category]].append((entity_id, globals()[entity_id]))
    return palette


def editable_properties(attr: str) -> List[Tuple[str, str]]:
    fields = list(EDITABLE_PROPERTIES.get(attr, []))
    if isinstance(globals().get(attr), Actor):
        fields += [("drop_name", "text"), ("drop_id", "quest_id"), ("on_death", "link_id")]
        fields += [  # overrides of this one placed actor, see level_editor.apply_overrides
            ("hp", "int"),
            ("power", "int"),
            ("armor", "int"),
            ("xp", "int"),
            ("ai", "choice:default," + ",".join(AI_OVERRIDES)),
        ]
    elif isinstance(globals().get(attr), Item):
        fields += [("on_pickup", "link_id")]
    return fields


def load_entities() -> None:
    """(Re)builds every prototype from the data files."""
    entries = entity_data.load_all()
    for problem in entity_data.problems(entries):
        print(f"Entity data: {problem}")
    for entity_id in CATEGORY:
        globals().pop(entity_id, None)
    CATEGORY.clear()
    for category, entry in entries:
        try:
            globals()[entry["id"]] = entity_data.build(entry, category)
        except Exception as exc:  # a broken entry should not stop the game
            print(f"Entity data: {entry.get('id', '?')} could not be built: {exc}")
            continue
        CATEGORY[entry["id"]] = category
    if not isinstance(globals().get(PLAYER_ID), Actor):
        print("Entity data: no player entry in actors.json, using the built-in one")
        globals()[PLAYER_ID] = fallback_player()
    globals()[PLAYER_ID].player_class = stats.DEFAULT_CLASS


def fallback_player() -> Actor:
    """Used when Data/actors.json has no usable player entry."""
    return Actor(
        char="@",
        color=(255, 255, 255),
        name="Player",
        ai_cls=HostileEnemy,
        equipment=Equipment(),
        fighter=Fighter(base_hp=30, base_armor=0, base_power=2, main_stat=5),
        inventory=Inventory(capacity=26),
        level=Level(level_up_base=0),
        spellbook=SpellBook(10),
        logbook=LogBook(),
        effect=DefaultEffect(),
    )


load_entities()
