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
        self.is_applied = False


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
    def __init__(
        self,
        equipment_type,
        stat_bonus: dict = {"TM": 0, "NS": 0, "FI": 0, "CD": 0, "PE": 0, "VI": 0},
    ):
        super().__init__(
            equipment_type=equipment_type,
            stat_bonus=stat_bonus,
        )


class WierdRing(Ring):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.RING,
            stat_bonus={"TM": 0, "NS": 0, "FI": 0, "CD": 1, "PE": 0, "VI": 0},
        )

class OssuaryLoop(Ring):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.RING,
            stat_bonus={"TM": 2, "NS": 0, "FI": 1, "CD": 0, "PE": 0, "VI": 0},
        )


class Veinbinder(Ring):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.RING,
            stat_bonus={"TM": 0, "NS": 2, "FI": -1, "CD": 0, "PE": 0, "VI": 1},
        )


class WeepingKnuckle(Ring):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.RING,
            stat_bonus={"TM": 0, "NS": 0, "FI": 1, "CD": 0, "PE": 2, "VI": 0},
        )


class PhageCirclet(Ring):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.RING,
            stat_bonus={"TM": 0, "NS": 0, "FI": -1, "CD": 2, "PE": 0, "VI": 1},
        )


class Stitchband(Ring):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.RING,
            stat_bonus={"TM": 1, "NS": 1, "FI": 1, "CD": 0, "PE": 0, "VI": 0},
        )


class MawsEmbrace(Ring):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.RING,
            stat_bonus={"TM": 2, "NS": 0, "FI": 0, "CD": 0, "PE": -1, "VI": 1},
        )


class CarrionLoop(Ring):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.RING,
            stat_bonus={"TM": 0, "NS": 0, "FI": 2, "CD": 0, "PE": 1, "VI": 0},
        )


class ThrobbingHalo(Ring):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.RING,
            stat_bonus={"TM": 0, "NS": 1, "FI": 0, "CD": 1, "PE": 2, "VI": 0},
        )


class TumorsPromise(Ring):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.RING,
            stat_bonus={"TM": 1, "NS": 0, "FI": 2, "CD": 0, "PE": 0, "VI": -1},
        )


class KnottedVisceraBand(Ring):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.RING,
            stat_bonus={"TM": 1, "NS": 0, "FI": 1, "CD": 1, "PE": 0, "VI": 0},
        )
