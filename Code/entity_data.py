"""Items and actors as data: Data/items.json, Data/equipment.json, Data/actors.json.

Logic stays in code and is picked by name from a registry:
  EFFECT_TYPES      what eating a corpse does (components/effects.py)
  CONSUMABLE_TYPES  what using an item does (components/consumable.py)
  AI_TYPES          how an actor behaves (components/ai.py)
Effects and consumables are found automatically, together with the numbers
their constructors take, so a new class there shows up in the editor as is.

entity_factory loads the files and makes every entry a module attribute under
its id, so entity_factory.health_potion and saved levels keep working.
"""
from __future__ import annotations

import inspect
import json
import os
import re
from typing import List, Tuple

from components import ai, consumable, effects
from components.effects import LogBook
from components.equipment import Equipment
from components.equippable import Equippable
from components.fighter import Fighter
from components.inventory import Inventory
from components.level import Level
from components.settings import DATA_DIR
from components.spells import SpellBook
from entity import Actor, Entity, Item
from equipment_types import EquipmentType

FORMAT = "flesh-tower-entities"
FORMAT_VERSION = 1

# data file -> palette group in the level editor, in palette order
CATEGORIES = {"actors": "Monsters", "items": "Items", "equipment": "Equipment"}


def snake(name: str, suffix: str = "") -> str:
    """HealingScrollEffect -> healing_scroll (with suffix "Effect")."""
    if suffix and name.endswith(suffix) and name != suffix:
        name = name[: -len(suffix)]
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def subclasses(module, base) -> list:
    return [
        obj
        for obj in vars(module).values()
        if inspect.isclass(obj)
        and issubclass(obj, base)
        and obj is not base
        and obj.__module__ == module.__name__
    ]


def params_of(cls) -> List[Tuple[str, str]]:
    """Constructor arguments as editor fields: (name, "int" or "text")."""
    fields = []
    for param in list(inspect.signature(cls.__init__).parameters.values())[1:]:
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            continue
        is_int = "int" in str(param.annotation) or (
            type(param.default) is int  # not bool
        )
        fields.append((param.name, "int" if is_int else "text"))
    return fields


EFFECT_TYPES = {snake(cls.__name__, "Effect"): cls for cls in subclasses(effects, effects.Effect)}
CONSUMABLE_TYPES = {
    snake(cls.__name__, "Consumable"): cls
    for cls in subclasses(consumable, consumable.Consumable)
}
AI_TYPES = {
    "hostile": ai.HostileEnemy,
    "caster": ai.HostileCaster,
    "neutral": ai.Vendor,  # stands still, never attacks
    "abomination": ai.ViceraAbomination,
    "corpse_fly": ai.BloatedCorpseFly,
}
SLOTS = {slot.name.lower(): slot for slot in EquipmentType}


# --- data -> entity ---


def make_component(registry: dict, spec: dict):
    """{"type": "healing", "amount": 15} -> HealingConsumable(amount=15)."""
    cls = registry[spec["type"]]
    kwargs = {name: spec[name] for name, _ in params_of(cls) if name in spec}
    return cls(**kwargs)


def build(entry: dict, category: str) -> Entity:
    common = dict(
        char=entry["char"],
        color=tuple(entry["color"]),
        name=entry["name"],
        effect=make_component(EFFECT_TYPES, entry.get("effect") or {"type": "default"}),
    )
    if category == "actors":
        return Actor(
            **common,
            ai_cls=AI_TYPES[entry.get("ai", "hostile")],
            equipment=Equipment(),
            fighter=Fighter(
                base_hp=entry.get("hp", 1),
                base_armor=entry.get("armor", entry.get("defense", 0)),
                base_power=entry.get("power", 0),
                main_stat=entry.get("main_stat", 0),
            ),
            inventory=Inventory(capacity=entry.get("inventory", 0)),
            level=Level(xp_given=entry.get("xp", 0)),
            spellbook=SpellBook(entry.get("spell_slots", 0)),
            logbook=LogBook(),
        )

    gear = entry.get("equippable")
    return Item(
        **common,
        price=entry.get("price", 0),
        quest_id=entry.get("quest_id"),
        consumable=make_component(CONSUMABLE_TYPES, entry["consumable"])
        if entry.get("consumable")
        else None,
        equippable=Equippable(
            equipment_type=SLOTS[gear["slot"]],
            power_bonus=gear.get("power", 0),
            armor_bonus=gear.get("armor", gear.get("defense", 0)),
        )
        if gear
        else None,
    )


# --- entity -> data (migration, and the editor saving) ---


def component_spec(registry: dict, obj) -> dict:
    name = next(key for key, cls in registry.items() if type(obj) is cls)
    spec = {"type": name}
    for param, _ in params_of(type(obj)):
        spec[param] = getattr(obj, param)
    return spec


def to_entry(entity_id: str, entity: Entity) -> Tuple[str, dict]:
    """(category, entry) describing a prototype."""
    entry = {"id": entity_id, "name": entity.name, "char": entity.char, "color": list(entity.color)}
    if isinstance(entity, Actor):
        entry.update(
            ai=next(key for key, cls in AI_TYPES.items() if type(entity.ai) is cls),
            hp=entity.fighter.base_hp,
            power=entity.fighter.base_power,
            armor=entity.fighter.base_armor,
            xp=entity.level.xp_given,
            inventory=entity.inventory.capacity,
            spell_slots=entity.spellbook.capacity,
        )
        category = "actors"
    else:
        entry["price"] = entity.price
        if entity.quest_id:
            entry["quest_id"] = entity.quest_id
        if entity.consumable:
            entry["consumable"] = component_spec(CONSUMABLE_TYPES, entity.consumable)
        if entity.equippable:
            gear = entity.equippable
            entry["equippable"] = {
                "slot": gear.equipment_type.name.lower(),
                "power": gear.power_bonus,
                "armor": gear.armor_bonus,
            }
        category = "equipment" if entity.equippable else "items"
    entry["effect"] = component_spec(EFFECT_TYPES, entity.effect)
    return category, entry


# --- files ---


def data_file(category: str) -> str:
    return os.path.join(DATA_DIR, f"{category}.json")


def load_category(category: str) -> List[dict]:
    path = data_file(category)
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if data.get("format") != FORMAT:
        raise ValueError(f"{path} is not an entity file")
    return data.get("entries", [])


def load_all() -> List[Tuple[str, dict]]:
    return [(category, entry) for category in CATEGORIES for entry in load_category(category)]


def save_category(category: str, entries: List[dict]) -> None:
    """One entry per line, so git diffs show which entity changed."""
    os.makedirs(DATA_DIR, exist_ok=True)
    lines = [json.dumps(entry, ensure_ascii=False) for entry in entries]
    text = (
        "{\n"
        f'  "format": "{FORMAT}",\n'
        f'  "version": {FORMAT_VERSION},\n'
        '  "entries": [\n    '
        + ",\n    ".join(lines)
        + "\n  ]\n}\n"
    )
    path = data_file(category)
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(path + ".tmp", path)  # never leave a half written file


def problems(entries: List[Tuple[str, dict]]) -> List[str]:
    """Anything a loaded file gets wrong, as readable lines."""
    found, seen = [], set()
    for category, entry in entries:
        entity_id = entry.get("id", "?")
        if entity_id in seen:
            found.append(f"{entity_id}: id used twice")
        seen.add(entity_id)
        for key in ("name", "char", "color"):
            if key not in entry:
                found.append(f"{entity_id}: missing {key}")
        effect = (entry.get("effect") or {}).get("type", "default")
        if effect not in EFFECT_TYPES:
            found.append(f"{entity_id}: unknown effect {effect}")
        if entry.get("consumable") and entry["consumable"].get("type") not in CONSUMABLE_TYPES:
            found.append(f"{entity_id}: unknown consumable {entry['consumable'].get('type')}")
        if entry.get("equippable") and entry["equippable"].get("slot") not in SLOTS:
            found.append(f"{entity_id}: unknown slot {entry['equippable'].get('slot')}")
        if category == "actors" and entry.get("ai", "hostile") not in AI_TYPES:
            found.append(f"{entity_id}: unknown ai {entry.get('ai')}")
    return found
