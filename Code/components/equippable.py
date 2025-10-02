from __future__ import annotations

from typing import TYPE_CHECKING

from components.base_component import BaseComponent
from equipment_types import EquipmentType

if TYPE_CHECKING:
    from entity import Item


class Equippable(BaseComponent):
    parent: Item

    def __init__(
        self,
        equipment_type: EquipmentType,
        power_bonus: int = 0,
        defense_bonus: int = 0,
        stat_bonus: dict = {},
    ):
        self.equipment_type = equipment_type
        self.power_bonus = power_bonus
        self.defense_bonus = defense_bonus
        self.stat_bonus = stat_bonus


class Dagger(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.WEAPON, power_bonus=2)


class Sword(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.WEAPON, power_bonus=4)


class LeatherArmor(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.ARMOR, defense_bonus=1)


class ChainMail(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.ARMOR, defense_bonus=3)


class Ring(Equippable):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.RING,
            stat_bonus={"TM": 0, "NS": 0, "FI": 0, "CD": 0, "PE": 0, "VI": 0},
        )


class WierdRing(Ring):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.RING,
            stat_bonus={"TM": 0, "NS": 0, "FI": 0, "CD": 5, "PE": 0, "VI": 0},
        )
