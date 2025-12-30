from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from components.base_component import BaseComponent
from equipment_types import EquipmentType

if TYPE_CHECKING:
    from entity import Actor, Item


class Equipment(BaseComponent):
    parent: Actor

    def __init__(
        self,
        weapon: Optional[Item] = None,
        ring0: Optional[Item] = None,
        ring1: Optional[Item] = None,
        ring2: Optional[Item] = None,
        ring3: Optional[Item] = None,
        ring4: Optional[Item] = None,
        ring5: Optional[Item] = None,
        ring6: Optional[Item] = None,
        ring7: Optional[Item] = None,
        ring8: Optional[Item] = None,
        ring9: Optional[Item] = None,
        armor: Optional[Item] = None,
        head: Optional[Item] = None,
        eyes: Optional[Item] = None,
        necklace: Optional[Item] = None,
        cloak: Optional[Item] = None,
        wrist: Optional[Item] = None,
        belt: Optional[Item] = None,
        legs: Optional[Item] = None,
    ):
        self.weapon = weapon
        self.armor = armor
        self.ring0 = ring0
        self.ring1 = ring1
        self.ring2 = ring2
        self.ring3 = ring3
        self.ring4 = ring4
        self.ring5 = ring5
        self.ring6 = ring6
        self.ring7 = ring7
        self.ring8 = ring8
        self.ring9 = ring9
        self.head = head
        self.eyes = eyes
        self.necklace = necklace
        self.cloak = cloak
        self.wrist = wrist
        self.belt = belt
        self.legs = legs

    @property
    def defence_bonus(self) -> int:
        bonus = 0
        if self.weapon is not None and self.weapon.equippable is not None:
            bonus += self.weapon.equippable.defense_bonus

        if self.armor is not None and self.armor.equippable is not None:
            bonus += self.armor.equippable.defense_bonus

        return bonus

    @property
    def power_bonus(self) -> int:
        bonus = 0

        if self.weapon is not None and self.weapon.equippable is not None:
            bonus += self.weapon.equippable.power_bonus

        if self.armor is not None and self.armor.equippable is not None:
            bonus += self.armor.equippable.power_bonus

        return bonus

    def stat_bonus(self, action_type, slot_give):
        multiplyer = 1 if action_type == "+" else -1
        # if not self.check_relevant_equip(equip, slot_give):
        slot = getattr(self, slot_give)
        for i in slot.equippable.stat_bonus:
            self.engine.player.fighter.bonus_stats[i] += (
                multiplyer * slot.equippable.stat_bonus[i]
            )
        self.engine.player.fighter.bonus_power += (
            multiplyer * slot.equippable.power_bonus
        )
        self.engine.player.fighter.bonus_defense += (
            multiplyer * slot.equippable.defense_bonus
        )
        if action_type == "+":
            slot.equippable.is_applied = True
        else:
            slot.equippable.is_applied = False
        # forgot to derive stats, now effects get correctly applied
        self.engine.player.fighter.derive_stats()

    def item_is_equipped(self, item: Item) -> bool:
        # new logic allows for dynamic check if any slot is currently equipped
        for i in self.__dict__:
            if "_" not in i and getattr(self, i) == item:
                return getattr(self, i) == item

        return False

    def unequip_message(self, item_name: str) -> None:
        self.parent.gamemap.engine.message_log.add_message(f"You remove {item_name}")

    def equip_message(self, item_name: str) -> None:
        self.parent.gamemap.engine.message_log.add_message(f"You equip  {item_name}.")

    def equip_to_slot(self, slot: str, item: Item, add_message: bool) -> None:
        current_item = getattr(self, slot)

        if current_item is not None:
            self.unequip_from_slot(slot, add_message)

        setattr(self, slot, item)
        self.stat_bonus("+", slot)

        if add_message:
            self.equip_message(item.name)

    def unequip_from_slot(self, slot: str, add_message: bool) -> None:
        current_item = getattr(self, slot)

        if add_message:
            self.unequip_message(current_item.name)
        # stats need to be done before item is removed.
        # to remove stats stats need to be known :D
        self.stat_bonus("-", slot)
        setattr(self, slot, None)

    def toggle_equip(self, equippable_item: Item, add_message: bool = True) -> None:
        # TODO total rewrite
        # possibly assign empty slots the corrispnding Types from EquipmentType.
        # loop at all slots via __dict__ and find slot for everything except rings
        # in unequip instead of setting slot to None set to EquipmentType again?
        # this would make this so much less cumbersome of a methode
        slot = ""
        if (
            equippable_item.equippable
            and equippable_item.equippable.equipment_type == EquipmentType.WEAPON
        ):
            slot = "weapon"
        elif (
            equippable_item.equippable
            and equippable_item.equippable.equipment_type == EquipmentType.ARMOR
        ):
            slot = "armor"
        elif (
            equippable_item.equippable
            and equippable_item.equippable.equipment_type == EquipmentType.RING
        ):
            # logic allows for the equipping of up to 10 rings
            # first get first free slot
            for i in range(9):
                slot_name = f"ring{i}"
                if getattr(self, slot_name) is None:
                    slot = slot_name
                    break
            # check if unequip is necesarry
            for i in range(9):
                slot_name = f"ring{i}"
                if getattr(self, slot_name) == equippable_item:
                    slot = slot_name
                    break
        elif (
            equippable_item.equippable
            and equippable_item.equippable.equipment_type == EquipmentType.HEAD
        ):
            slot = "head"
        elif (
            equippable_item.equippable
            and equippable_item.equippable.equipment_type == EquipmentType.EYES
        ):
            slot = "eyes"
        elif (
            equippable_item.equippable
            and equippable_item.equippable.equipment_type == EquipmentType.NECKLACE
        ):
            slot = "necklace"
        elif (
            equippable_item.equippable
            and equippable_item.equippable.equipment_type == EquipmentType.CLOAK
        ):
            slot = "cloak"
        elif (
            equippable_item.equippable
            and equippable_item.equippable.equipment_type == EquipmentType.WRIST
        ):
            slot = "wrist"
        elif (
            equippable_item.equippable
            and equippable_item.equippable.equipment_type == EquipmentType.BELT
        ):
            slot = "belt"
        elif (
            equippable_item.equippable
            and equippable_item.equippable.equipment_type == EquipmentType.LEGS
        ):
            slot = "legs"

        if getattr(self, slot) == equippable_item:
            self.unequip_from_slot(slot, add_message)
        else:
            self.equip_to_slot(slot, equippable_item, add_message)
