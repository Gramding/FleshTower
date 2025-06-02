from __future__ import annotations

from typing import TYPE_CHECKING, Optional
import color
from components.base_component import BaseComponent
from render_order import RenderOrder
from components.spells import Spell

if TYPE_CHECKING:
    from entity import Actor


class Fighter(BaseComponent):
    parent: Actor

    def __init__(
        self,
        hp: int,
        base_defense: int,
        base_power: int,
        # consumption: Optional[ConsumeCorpse],
    ):
        self.max_hp = hp
        self.mana = 0
        self.max_mana = 0
        self._hp = hp
        self.base_defense = base_defense
        self.base_power = base_power

    @property
    def hp(self) -> int:
        return self._hp

    @hp.setter
    def hp(self, value: int) -> None:
        # this enshures that HP can never be negative
        # and never more than maximum
        self._hp = max(0, min(value, self.max_hp))
        if self._hp == 0 and self.parent.ai:
            self.die()

    @property
    def defense(self) -> int:
        return self.base_defense + self.defense_bonus

    @property
    def power(self) -> int:
        return self.base_power + self.power_bonus

    @property
    def defense_bonus(self) -> int:
        if self.parent.equipment:
            return self.parent.equipment.defence_bonus
        else:
            return 0

    @property
    def power_bonus(self) -> int:
        if self.parent.equipment:
            return self.parent.equipment.power_bonus
        else:
            return 0

    def die(self) -> None:
        if self.engine.player is self.parent:
            death_message = "Your flesh becomes part of the tower"
            death_message_color = color.player_die
        else:
            death_message = f"{self.parent.name} returns to the tower"
            death_message_color = color.enemy_die

        self.parent.char = "%"
        self.parent.color = (191, 0, 0)
        self.parent.blocks_movement = False
        self.parent.ai = None
        self.parent.name = f"remains of {self.parent.name}"
        self.parent.render_order = RenderOrder.CORPSE

        self.engine.message_log.add_message(death_message, death_message_color)
        self.engine.player.level.add_xp(self.parent.level.xp_given)

    def heal(self, amount: int) -> int:
        # check if at full HP
        if self.hp == self.max_hp:
            return 0
        # calc new hp value
        new_hp_value = self.hp + amount
        # if larger than max set to max
        if new_hp_value > self.max_hp:
            new_hp_value = self.max_hp
        # amount healed
        amount_recovered = new_hp_value - self.hp
        # set HP
        self.hp = new_hp_value

        return amount_recovered

    def heal_mana(self, amount: int) -> int:
        if self.mana == self.max_mana:
            return 0
        new_mana = self.mana + amount

        if new_mana > self.max_mana:
            new_mana = self.max_mana
        amount_recovered = new_mana - self.mana
        self.mana = new_mana

        return amount_recovered

    def take_damage(self, amount: int, ignore_defence: Optional[bool] = False) -> int:
        if not ignore_defence:
            self.hp -= amount - self.defense
            return amount - self.defense
        else:
            self.hp -= amount
            return amount

    def cast_spell(self, spell: Spell) -> bool:
        if self.mana >= spell.mana_cost:
            self.mana -= spell.mana_cost
            return True
        return False
