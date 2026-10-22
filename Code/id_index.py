"""Who uses which id: one table for the level editor's lookups and checks.

Every use of an id in the levels and dialogues becomes a Use:
    kind   signal, flag, quest, lore, loot_table, dialogue
    role   signal: sends / receives   flag: sets / reads
           quest: gives / uses        files: uses
Saved levels and dialogues are read once and cached until their file
changes; the level open in the editor is read fresh every time.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import rules
from components.dialouge_parser import list_dialogues, load_dialogue, quest_key
from components.settings import DIALOGUE_DIR
from tiles import SIGNAL_PROPERTIES, TILE_BY_ID


@dataclass(frozen=True)
class Use:
    kind: str
    id: str
    role: str
    label: str  # what uses it, e.g. "Door", "rat on_death", "'Yes'"
    source: str  # level name or dialogue file
    pos: Optional[Tuple[int, int]] = None
    current: bool = False  # in the level open in the editor

    @property
    def where(self) -> str:
        at = f" at {self.pos[0]},{self.pos[1]}" if self.pos else ""
        return f"{self.source}: {self.label}{at}"


def condition_uses(conditions, label, source, pos, current) -> List[Use]:
    uses = []
    for kind, value in conditions:
        value = quest_key(value)
        if kind in ("if", "ifnot"):
            uses.append(Use("flag", value, "reads", label, source, pos, current))
        elif kind == "requires":
            uses.append(Use("quest", value, "uses", label, source, pos, current))
    return uses


def action_uses(action: str, props: dict, label, source, pos, current) -> List[Use]:
    def use(kind, value, role):
        return Use(kind, value, role, f"{label} {action}", source, pos, current)

    if action == "signal" and props.get("target"):
        return [use("signal", quest_key(props["target"]), "sends")]
    if action in ("flag", "unflag") and props.get("flag"):
        return [use("flag", quest_key(props["flag"]), "sets")]
    if action == "gives" and props.get("item") and rules.item_prototype(props["item"]) is None:
        return [use("quest", quest_key(props["item"]), "gives")]
    if action == "takes" and props.get("item"):
        return [use("quest", quest_key(props["item"]), "uses")]
    if action == "lore" and props.get("lore"):
        return [use("lore", props["lore"], "uses")]
    return []


def level_uses(level, current: bool = False) -> List[Use]:
    source = level.name or "this level"
    uses: List[Use] = []
    for pos, props in level.properties.items():
        tile = TILE_BY_ID.get(int(level.tiles[pos]))
        attr = level.entities.get(pos)
        label = tile.name if tile is not None and tile.properties else (attr or "?")

        def add(kind, value, role, what=label):
            if value:
                uses.append(Use(kind, value, role, what, source, pos, current))

        if tile is not None and tile.link:
            add("signal", quest_key(props.get("signal", "")), tile.link)
        if props.get("gives") and rules.item_prototype(props["gives"]) is None:  # chest
            add("quest", quest_key(props["gives"]), "gives", f"{label} gives")
        if tile is not None and tile.event:
            uses += action_uses(props.get("action", ""), props, label, source, pos, current)
        if attr:
            for key in SIGNAL_PROPERTIES:  # on_death / on_pickup
                add("signal", quest_key(props.get(key, "")), "sends", f"{attr} {key}")
            add("quest", quest_key(props.get("quest", "")), "gives", f"{attr} on the floor")
            if rules.item_prototype(props.get("drop", "")) is None:
                add("quest", quest_key(props.get("drop", "")), "gives", f"dropped by {attr}")
            add("dialogue", props.get("dialogue", ""), "uses")
        if tile is None or not tile.event:  # an event's lore counts as its action
            add("lore", props.get("lore", ""), "uses")
        add("loot_table", props.get("loot_table", ""), "uses")
        uses += condition_uses(rules.conditions_from_props(props), label, source, pos, current)
    for area in getattr(level, "areas", []):
        pos = tuple(area["rect"][:2])
        props = area["props"]
        if props.get("signal"):
            uses.append(Use("signal", quest_key(props["signal"]), "sends", "Area", source, pos, current))
        uses += condition_uses(rules.conditions_from_props(props), "Area", source, pos, current)
    return uses


def dialogue_uses_of(filename: str, dialogue) -> List[Use]:
    uses: List[Use] = []
    for passage in dialogue.passages.values():
        label = f"'{passage.name}'"
        uses += condition_uses(rules.conditions_from_tags(passage.tags), label, filename, None, False)
        for action, props in rules.tag_actions(passage.tags):
            uses += action_uses(action, props, label, filename, None, False)
    return uses


# --- cache of files on disk ----------------------------------------------------

_level_cache: Dict[str, Tuple[float, str, List[Use]]] = {}  # file -> (mtime, name, uses)
_dialogue_cache: Dict[str, Tuple[float, List[Use]]] = {}


def mtime(path: str) -> float:
    try:
        return os.path.getmtime(path)
    except OSError:
        return -1.0


def saved_level_uses(skip_name: str = "") -> List[Use]:
    from level_editor import list_levels, load_level

    uses: List[Use] = []
    for _, filename in list_levels():
        stamp = mtime(filename)
        cached = _level_cache.get(filename)
        if cached is None or cached[0] != stamp:
            try:
                level = load_level(filename)
            except Exception:
                continue
            cached = (stamp, level.name, level_uses(level))
            _level_cache[filename] = cached
        if skip_name and cached[1] == skip_name:
            continue  # the open version replaces the saved one
        uses += cached[2]
    return uses


def dialogue_uses() -> List[Use]:
    uses: List[Use] = []
    for _, filename in list_dialogues():
        path = os.path.join(DIALOGUE_DIR, filename)
        stamp = mtime(path)
        cached = _dialogue_cache.get(filename)
        if cached is None or cached[0] != stamp:
            try:
                found = dialogue_uses_of(filename, load_dialogue(path))
            except Exception:
                found = []
            cached = (stamp, found)
            _dialogue_cache[filename] = cached
        uses += cached[1]
    return uses


def all_uses(current=None) -> List[Use]:
    """Every use in every level (the open one instead of its saved copy) and
    every dialogue."""
    uses = saved_level_uses(current.name if current is not None else "")
    if current is not None:
        uses += level_uses(current, current=True)
    return uses + dialogue_uses()


def counts(uses: List[Use]) -> List[Tuple[str, int]]:
    """(id, uses), most used first, for autocomplete."""
    found: Dict[str, int] = {}
    for use in uses:
        found[use.id] = found.get(use.id, 0) + 1
    return sorted(found.items(), key=lambda item: -item[1])


# --- questions the editor's id fields ask -------------------------------------

OPPOSITE = {"sends": "receives", "receives": "sends", "sets": "reads", "reads": "sets",
            "gives": "uses", "uses": "gives"}
MISSING = {
    ("signal", "receives"): "Nothing reacts to this signal yet",
    ("signal", "sends"): "Nothing triggers this signal yet",
    ("flag", "sets"): "Nothing sets this flag yet",
    ("flag", "reads"): "Nothing checks this flag yet",
    ("quest", "gives"): "Nothing gives this item yet",
    ("quest", "uses"): "Nothing needs this item yet",
}
KIND_LABELS = {"signal": "Signal", "flag": "Flag", "quest": "Quest item"}


def related(kind: str, current) -> List[Use]:
    """Uses an id of this kind can meet: signals only work inside one level
    (plus dialogue tags), flags and quest items everywhere."""
    if kind == "signal":
        level = level_uses(current, current=True) if current is not None else []
        return [u for u in level + dialogue_uses() if u.kind == "signal"]
    return [u for u in all_uses(current) if u.kind == kind]


def uses_of(kind: str, value: str, current=None, skip_pos=None) -> List[str]:
    """Readable places that use this id or file, except the field being edited."""
    uses = related(kind, current) if kind in KIND_LABELS else all_uses(current)
    return [
        use.where
        for use in uses
        if use.kind == kind and use.id == value and not (use.current and use.pos == skip_pos)
    ]


def suggestions(kind: str, current=None) -> List[Tuple[str, int]]:
    """(id, uses) for autocomplete, most used first."""
    from tiles import START_SIGNAL

    found = counts(related(kind, current))
    if kind == "signal" and START_SIGNAL not in dict(found):
        found.append((START_SIGNAL, 0))
    return found


def describe(kind: str, value: str, role: str, current=None, skip_pos=None) -> List[str]:
    """Popup lines after typing an id: who else uses it, and what is missing."""
    from tiles import START_SIGNAL

    uses = [
        use
        for use in related(kind, current)
        if use.id == value and not (use.current and use.pos == skip_pos)
    ]
    lines = [f"{KIND_LABELS.get(kind, kind)} '{value}'", ""]
    if uses:
        lines.append("Also used by:")
        lines += [f"{use.role}: {use.where}" for use in uses[:12]]
        if len(uses) > 12:
            lines.append(f"... and {len(uses) - 12} more")
    else:
        lines.append("Not used anywhere else yet")
    needed = OPPOSITE.get(role)
    if kind == "signal" and value == START_SIGNAL:
        lines += ["", "Fired when the level starts"]
    elif needed and not any(use.role == needed for use in uses):
        lines += ["", MISSING[(kind, needed)]]
    return lines
