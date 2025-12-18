from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Dict
import random
import color
import copy
from components.base_component import BaseComponent
from render_order import RenderOrder
from components.spells import Spell
import math
from components.consumption import *
from components.settings import GENERAL_CHEATS

if TYPE_CHECKING:
    from entity import Actor


class Fighter(BaseComponent):
    parent: Actor

    def __init__(
        self,
        base_hp: int,
        base_defense: int,
        base_power: int,
        stats: Dict[str, int],
        # consumption: Optional[ConsumeCorpse],
    ):
        self.stats = {}
        self.base_stats = stats
        self.bonus_stats = {"TM": 0, "NS": 0, "FI": 0, "CD": 0, "PE": 0, "VI": 0}

        # HP
        self.base_hp = base_hp
        self.max_hp = base_hp
        self._hp = self.max_hp

        # MANA
        self.base_mana = 30
        self.mana = int(0)
        self.max_mana = 0

        # POWER
        self.bonus_power = 0
        self.base_power = base_power
        self.power = 0

        # ATTACKS
        self.base_attack_count = 1
        self.bonus_attack_count = 0
        self.attack_count = 0

        # DEFENCE
        self.base_defense = base_defense
        self.defense = 0
        self.bonus_defense = 0
        self.damage_reduction_base = 5
        self.damage_reduction = 0

        # MAGIC
        self.spell_damage_bonus = 0
        self.spell_cost_reduction = 0

        # SHOP DISCOUNT
        self.price_discount = 0

        # STAMINA
        self.base_stamina = 30
        self.max_stamina = 0
        self.stamina = 0

        # MASS
        self.mass = 0
        self.max_mass = 30
        self.mass_level = 0

        self.current_effecs = []

        self.derive_stats(req_hp_reset=True)

        # TODO Add modifiers like when going up the staris the player gains an affixe or sth.

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

        # 20% chance to drop an item on death
        # drop item on death
        if random.randint(0, 100) < 11110 and len(self.parent.inventory.items) > 0:
            item = random.choice(self.parent.inventory.items)
            clone = copy.deepcopy(item)
            clone.place(x=self.parent.x, y=self.parent.y, gamemap=self.engine.game_map)
            self.engine.message_log.add_message(
                f"{self.parent.name.replace('remains of ', '')} dropped {clone.name}"
            )

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
        self.mana = int(new_mana)

        return int(amount_recovered)

    def take_damage(self, amount: int, ignore_defence: Optional[bool] = False) -> int:
        if not ignore_defence:
            self.hp -= amount - self.defense
            return amount - self.defense
        else:
            self.hp -= amount
            return amount

    def cast_spell(self, spell: Spell) -> bool:
        true_cost = spell.mana_cost - (
            spell.mana_cost * (self.engine.player.fighter.spell_cost_reduction / 100)
        )
        if self.mana >= true_cost:
            if not GENERAL_CHEATS["inf_mana"]:
                self.mana -= true_cost
            return True
        return False

    def get_modifier_value(self, value: int) -> int:
        return math.ceil((value - 8) / 2)

    def derive_stats(self, req_hp_reset: Optional[bool] = False):
        # Apply stat bonuses
        for stat in self.base_stats:
            self.stats[stat] = self.base_stats[stat] + self.bonus_stats[stat]

        # Tendous Mass
        tm = self.get_modifier_value(self.stats["TM"])
        self.power = tm + self.base_power

        # Nerve Sync
        ns = self.get_modifier_value(self.stats["NS"])
        if self.damage_reduction + (self.damage_reduction_base * (ns * 2)) <= 50:
            if ns == 0:
                self.damage_reduction = self.damage_reduction_base
            else:
                self.damage_reduction = self.damage_reduction_base * (ns * 2)
        else:
            self.damage_reduction = 50
        self.max_stamina = self.base_stamina + (ns * 4)
        if req_hp_reset:
            self.stamina = self.max_stamina

        # Flesh Integrity
        fi = self.get_modifier_value(self.stats["FI"])
        self.max_hp = self.base_hp + (fi * 4)
        if req_hp_reset:
            self._hp = self.max_hp

        # Cerebral Drift
        cd = self.get_modifier_value(self.stats["CD"])
        self.spell_damage_bonus = cd

        # Perceptual Echo
        pe = self.get_modifier_value(self.stats["PE"])
        self.max_mana = self.base_mana + (pe * 4)
        if req_hp_reset:
            self.mana = self.base_mana + pe

        # Visceral Influence
        vi = self.get_modifier_value(self.stats["VI"])
        self.price_discount = vi
        self.spell_cost_reduction = vi * 2

        # Fighter Mass
        self.max_hp += self.mass_level * 4
        self.damage_reduction += self.mass_level * 2

        # Attack Count
        self.attack_count = self.base_attack_count + self.bonus_attack_count

        # Power
        self.power = self.base_power + self.bonus_power

        # Defense
        self.defense = self.base_defense + self.bonus_defense

    def derive_Effects(self):
        for effect in self.current_effecs:
            match effect:
                case "Zombie":
                    zombie(engine=self.engine)
                case "FlayedThrall":
                    flayed_thrall(engine=self.engine)
        self.derive_stats()

