"""Entity editor inside the level editor ([E]): create, duplicate and edit the
items and actors in Data/*.json (see entity_data.py).

An entity is edited as a flat form of strings in a PropertyMenu, e.g.
{"name": "Rat", "color": "88,57,39", "effect": "default", "effect.amount": "5"},
and turned back into a data entry when the form is closed.
"""
from __future__ import annotations

import copy
import re

from tcod import libtcodpy

import entity_data
import entity_factory
import input_handlers
from entity_data import AI_TYPES, CATEGORIES, CONSUMABLE_TYPES, EFFECT_TYPES, SLOTS, params_of

ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
NO_CONSUMABLE = "none"

NEW_ENTRIES = {
    "actors": {"name": "New Monster", "char": "m", "color": [200, 200, 200], "ai": "hostile",
               "hp": 5, "power": 1, "armor": 0, "xp": 5, "inventory": 0, "spell_slots": 0},
    "items": {"name": "New Item", "char": "!", "color": [200, 200, 200], "price": 10},
    "equipment": {"name": "New Gear", "char": "[", "color": [200, 200, 200], "price": 100,
                  "equippable": {"slot": "weapon", "power": 1, "armor": 0}},
}
ACTOR_NUMBERS = ("hp", "power", "armor", "xp", "inventory", "spell_slots")
PLAYER_NUMBERS = ("main_stat",)  # only the player entry has these


def choice(options) -> str:
    return "choice:" + ",".join(options)


def form_fields(category: str, form: dict) -> list:
    """Editor fields of an entity; consumable and effect numbers follow their type."""
    fields = [("name", "name"), ("char", "char"), ("color", "color")]
    if category == "actors":
        fields += [("ai", choice(AI_TYPES))] + [(key, "int") for key in ACTOR_NUMBERS]
        fields += [(key, "int") for key in PLAYER_NUMBERS if key in form]
    else:
        fields += [("price", "int")]
    if category == "items":
        fields += [("quest", "quest"),
                   ("consumable", choice([NO_CONSUMABLE] + list(CONSUMABLE_TYPES)))]
        consumable = CONSUMABLE_TYPES.get(form.get("consumable", ""))
        if consumable is not None:
            fields += [(f"consumable.{name}", kind) for name, kind in params_of(consumable)]
    if category == "equipment":
        fields += [("slot", choice(SLOTS)), ("power", "int"), ("armor", "int")]
    fields += [("effect", choice(EFFECT_TYPES))]
    effect = EFFECT_TYPES.get(form.get("effect", ""))
    if effect is not None:
        fields += [(f"effect.{name}", kind) for name, kind in params_of(effect)]
    return fields


def to_form(category: str, entry: dict) -> dict:
    form = {
        "name": entry.get("name", ""),
        "char": entry.get("char", "?"),
        "color": ",".join(str(part) for part in entry.get("color", [255, 255, 255])),
    }
    if category == "actors":
        form["ai"] = entry.get("ai", "hostile")
        for key in ACTOR_NUMBERS:
            form[key] = str(entry.get(key, 0))
        if "armor" not in entry:
            form["armor"] = str(entry.get("defense", 0))  # before the stat rework
        for key in PLAYER_NUMBERS:
            if key in entry:
                form[key] = str(entry[key])
    else:
        form["price"] = str(entry.get("price", 0))
    if entry.get("quest", entry.get("quest_id")):
        form["quest"] = entry.get("quest", entry.get("quest_id"))
    consumable = entry.get("consumable")
    form["consumable"] = consumable["type"] if consumable else NO_CONSUMABLE
    for key, value in (consumable or {}).items():
        if key != "type":
            form[f"consumable.{key}"] = str(value)
    if category == "equipment":
        gear = entry.get("equippable") or {}
        form.update(slot=gear.get("slot", "weapon"),
                    power=str(gear.get("power", 0)),
                    armor=str(gear.get("armor", gear.get("defense", 0))))
    effect = entry.get("effect") or {"type": "default"}
    form["effect"] = effect["type"]
    for key, value in effect.items():
        if key != "type":
            form[f"effect.{key}"] = str(value)
    return form


def from_form(category: str, entity_id: str, form: dict) -> dict:
    def number(key) -> int:
        try:
            return int(form.get(key, 0))
        except ValueError:
            return 0

    def params(prefix: str, cls) -> dict:
        found = {}
        for name, kind in params_of(cls):
            if f"{prefix}.{name}" in form:
                found[name] = number(f"{prefix}.{name}") if kind == "int" else form[f"{prefix}.{name}"]
        return found

    entry = {
        "id": entity_id,
        "name": form.get("name", ""),
        "char": form.get("char", "?"),
        "color": [int(part) for part in form.get("color", "255,255,255").split(",")],
    }
    if category == "actors":
        entry["ai"] = form.get("ai", "hostile")
        for key in ACTOR_NUMBERS + PLAYER_NUMBERS:
            if key in form:
                entry[key] = number(key)
    else:
        entry["price"] = number("price")
    if category == "items":
        if form.get("quest"):
            entry["quest"] = form["quest"]
        consumable = CONSUMABLE_TYPES.get(form.get("consumable", ""))
        if consumable is not None:
            entry["consumable"] = {"type": form["consumable"], **params("consumable", consumable)}
    if category == "equipment":
        entry["equippable"] = {"slot": form.get("slot", "weapon"),
                               "power": number("power"), "armor": number("armor")}
    effect_type = form.get("effect", "default")
    entry["effect"] = {"type": effect_type, **params("effect", EFFECT_TYPES[effect_type])}
    return entry


def find_entry(entity_id: str):
    category = entity_factory.CATEGORY[entity_id]
    for entry in entity_data.load_category(category):
        if entry["id"] == entity_id:
            return category, copy.deepcopy(entry)
    raise KeyError(entity_id)


def save_entry(category: str, entry: dict) -> None:
    entries = entity_data.load_category(category)
    for i, old in enumerate(entries):
        if old["id"] == entry["id"]:
            entries[i] = entry
            break
    else:
        entries.append(entry)
    entity_data.save_category(category, entries)


def id_problem(entity_id: str) -> str:
    if not ID_PATTERN.match(entity_id):
        return "Use a-z, 0-9 and _, start with a letter"
    if entity_id in entity_factory.CATEGORY:
        return f"{entity_id} already exists"
    if hasattr(entity_factory, entity_id):
        return f"{entity_id} is taken by the game code"
    return ""


def popup(parent, text: str):
    return input_handlers.PopupMessage(parent, text, halved=True, alignment=libtcodpy.CENTER)


def entity_list(editor):
    """[E] in the level editor: every entity, with + New on top."""
    entries = [("+ New entity...", None)]
    for entity_id, category in entity_factory.CATEGORY.items():
        prototype = getattr(entity_factory, entity_id)
        entries.append((f"{CATEGORIES[category]}: {prototype.name[:30]} ({entity_id})", entity_id))

    def pick(entity_id):
        if entity_id is None:
            return input_handlers.ListPicker(
                editor, "New entity", [(group, category) for category, group in CATEGORIES.items()],
                lambda category: ask_id(editor, category),
            )

        def choose(action):
            if action == "edit":
                category, entry = find_entry(entity_id)
                return edit_form(editor, category, entry)
            return ask_id(editor, entity_factory.CATEGORY[entity_id], copy_from=entity_id)

        return input_handlers.ListPicker(
            editor, entity_id, [("Edit", "edit"), ("Duplicate", "duplicate")], choose
        )

    return input_handlers.ListPicker(editor, "Entities", entries, pick)


def ask_id(editor, category: str, copy_from: str = ""):
    """Ids are what levels store, so they are chosen once and never renamed."""

    def submit(text):
        entity_id = text.strip().lower().replace(" ", "_").replace("-", "_")
        problem = id_problem(entity_id)
        if problem:
            prompt.error = problem
            return None
        if copy_from:
            _, entry = find_entry(copy_from)
        else:
            entry = copy.deepcopy(NEW_ENTRIES[category])
        entry["id"] = entity_id
        return edit_form(editor, category, entry, new=True)

    title = f"Id of the copy of {copy_from}" if copy_from else "Id of the new entity"
    prompt = input_handlers.TextPrompt(editor, title, "", submit)
    return prompt


def edit_form(editor, category: str, entry: dict, new: bool = False):
    """The entity as a property menu; Esc checks it, saves it and reloads it."""
    form = to_form(category, entry)

    def close():
        updated = from_form(category, entry["id"], form)
        if updated == entry and not new:
            return editor
        problems = entity_data.problems([(category, updated)])
        if not problems:
            try:
                entity_data.build(updated, category)  # would the game accept it?
            except Exception as exc:
                problems.append(f"can't be built: {exc}")
        if problems:
            return popup(menu, "Not saved:\n" + "\n".join(problems))
        save_entry(category, updated)
        entity_factory.load_entities()
        editor.refresh_palette()
        editor.status = f"Saved {updated['id']}"
        return editor

    menu = input_handlers.PropertyMenu(
        editor, None, lambda values: form_fields(category, values), values=form,
        title=f"{entry['id']} ({CATEGORIES[category]})", on_close=close, part_of_level=False,
    )
    return menu
