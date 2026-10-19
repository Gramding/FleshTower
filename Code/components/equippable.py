from __future__ import annotations

from typing import TYPE_CHECKING

from components.base_component import BaseComponent
from equipment_types import EquipmentType

if TYPE_CHECKING:
    from entity import Item


class Equippable(BaseComponent):
    """Slot and bonuses of a wearable item. Every piece of equipment is data
    now (Data/equipment.json, see entity_data.py)."""

    parent: Item

    def __init__(
        self,
        equipment_type: EquipmentType,
        power_bonus: int = 0,
        armor_bonus: int = 0,
    ):
        self.equipment_type = equipment_type
        self.power_bonus = power_bonus
        self.armor_bonus = armor_bonus

    def __setstate__(self, state: dict) -> None:
        # savegames from before the stat rework called armor "defense"
        if "defense_bonus" in state:
            state["armor_bonus"] = state.pop("defense_bonus")
        self.__dict__.update(state)


def __getattr__(name: str):
    """Savegames from before the data files point at one class per item
    (equippable.NeuralRazor ...). Those only ever set the fields above, so
    loading them as a plain Equippable keeps old saves working."""
    if name[:1].isupper():
        return Equippable
    raise AttributeError(name)
