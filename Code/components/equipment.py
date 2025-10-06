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
    ):
        self.weapon = weapon
        self.armor = armor
        # this is ok for now but needs to be changed somehow TODO
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

    def stat_bonus(self, action_type):
        for equip in self.__dict__:
            if "_" not in equip and "parent" not in equip:
                slot = getattr(self, equip)
                if slot and slot.equippable:
                    if slot.equippable is not None:
                        for i in slot.equippable.stat_bonus:
                            if (
                                action_type == "+"
                                and slot.equippable.is_applied == False
                            ):
                                self.engine.player.fighter.stats[
                                    i
                                ] += slot.equippable.stat_bonus[i]
                            else:
                                self.engine.player.fighter.stats[
                                    i
                                ] -= slot.equippable.stat_bonus[i]

                        if action_type == "+" and slot.equippable.is_applied == False:
                            slot.equippable.is_applied = True
                        else:
                            slot.equippable.is_applied = False
        #forgot to derive stats, now effects get correctly applied
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
        self.stat_bonus("+")

        if add_message:
            self.equip_message(item.name)

    def unequip_from_slot(self, slot: str, add_message: bool) -> None:
        current_item = getattr(self, slot)
        self.stat_bonus("-")

        if add_message:
            self.unequip_message(current_item.name)

        setattr(self, slot, None)

    def toggle_equip(self, equippable_item: Item, add_message: bool = True) -> None:
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
            # should work
            for i in range(9):
                slot_name = f"ring{i}"
                if (
                    getattr(self, slot_name) == equippable_item
                    or getattr(self, slot_name) == None
                ):
                    slot = slot_name
                    break
            # slot = "ring1"

        if getattr(self, slot) == equippable_item:
            self.unequip_from_slot(slot, add_message)
        else:
            self.equip_to_slot(slot, equippable_item, add_message)
