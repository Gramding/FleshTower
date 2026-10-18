"""Loot tables: named text files in LootTables/, used by chests.

    # comments start with #
    rolls: 1-3          how many items one chest gives, a number or min-max
    health_potion 35    an item from entity_factory and its weight
    dagger 5            (a missing weight counts as 1)

The built-in table "random" uses the random tower's loot for the current
floor (procgen.item_chances). Loot is rolled when a chest is opened.
"""
from __future__ import annotations

import os
import random
from dataclasses import dataclass, field
from typing import List, Tuple

from components.settings import LOOT_DIR

RANDOM_TABLE = "random"
RANDOM_ROLLS = (1, 2)

TEMPLATE = """# one item per line: name weight
rolls: 1-2
health_potion 10
mana_potion 10
"""


@dataclass
class LootTable:
    rolls: Tuple[int, int] = (1, 1)
    entries: List[Tuple[str, int]] = field(default_factory=list)  # (item name, weight)
    problems: List[str] = field(default_factory=list)


def item_names() -> List[str]:
    """Every item a loot table can name, for autocomplete and checks."""
    import entity_factory
    from entity import Item

    return sorted(
        name for name, value in vars(entity_factory).items() if isinstance(value, Item)
    )


def parse(text: str) -> LootTable:
    table = LootTable()
    known = set(item_names())
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line.lower().startswith("rolls:"):
            low, _, high = line.split(":", 1)[1].strip().partition("-")
            try:
                rolls = (int(low), int(high or low))
            except ValueError:
                table.problems.append(f"line {number}: rolls needs a number or min-max")
                continue
            if rolls[0] < 0 or rolls[0] > rolls[1]:
                table.problems.append(f"line {number}: rolls {rolls[0]}-{rolls[1]} is backwards")
                continue
            table.rolls = rolls
            continue
        parts = line.split()
        name, weight = parts[0], 1
        if len(parts) > 1:
            try:
                weight = int(parts[1])
            except ValueError:
                table.problems.append(f"line {number}: weight of {name} is not a number")
                continue
        if name not in known:
            table.problems.append(f"line {number}: there is no item called {name}")
            continue
        table.entries.append((name, weight))
    return table


def list_loot_tables() -> List[Tuple[str, str]]:
    os.makedirs(LOOT_DIR, exist_ok=True)
    return [
        (name[: -len(".txt")].replace("_", " "), name)
        for name in sorted(os.listdir(LOOT_DIR))
        if name.endswith(".txt")
    ]


def load(filename: str) -> LootTable:
    with open(os.path.join(LOOT_DIR, filename), encoding="utf-8") as f:
        return parse(f.read())


def roll(engine, table_name: str) -> list:
    """Item prototypes for one chest opening; spawn copies of them."""
    import entity_factory

    if table_name == RANDOM_TABLE:
        import procgen

        floor = max(engine.game_world.current_floor, 0)
        count = random.randint(*RANDOM_ROLLS)
        return list(procgen.get_entities_at_random(procgen.item_chances, count, floor))

    try:
        table = load(table_name)
    except OSError:
        return []
    weights = [weight for _, weight in table.entries]
    if sum(weights) <= 0:
        return []
    count = random.randint(*table.rolls)
    names = random.choices([name for name, _ in table.entries], weights=weights, k=count)
    return [getattr(entity_factory, name) for name in names]
