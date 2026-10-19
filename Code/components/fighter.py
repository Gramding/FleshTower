from __future__ import annotations

from typing import TYPE_CHECKING, Optional
import random
import color
import copy
from components.base_component import BaseComponent
from render_order import RenderOrder
from components.spells import Spell
import math
from components.consumption import ConsumptionFactory
from components.settings import GENERAL_CHEATS
from components import stats

if TYPE_CHECKING:
    from entity import Actor


class Fighter(BaseComponent):
    """HP, damage and armor of an actor. Only base values and bonuses are
    stored; everything combat reads is computed (see components/stats.py).
    Monsters use base_hp, base_power and base_armor. The player adds a class
    main stat (STR, DEX or INT), gear, affix bonuses and a class resource."""

    parent: Actor

    def __init__(
        self,
        base_hp: int,
        base_armor: int,
        base_power: int,
        main_stat: int = 0,
    ):
        self.base_hp = base_hp
        self.base_power = base_power
        self.base_armor = base_armor
        self.main_stat = main_stat

        # from affixes (components/affix.py) and corpse effects
        self.bonus_hp = 0
        self.bonus_stat = 0
        self.bonus_armor = 0
        self.bonus_attacks = 0
        self.bonus_mana = 0
        self.bonus_stamina = 0
        self.bonus_mana_regen = 0  # turns faster
        self.sprint_discount = 0
        self.bonus_mass_gain = 0
        self.bonus_mass_armor = 0  # extra armor per mass level

        self._hp = self.max_hp

        # class resources
        self.mana = stats.BASE_MANA
        self.mana_regen_progress = 0
        self.stamina = stats.BASE_STAMINA
        self.mass = 0
        self.max_mass = 30
        self.mass_level = 0

        self.current_effects = []

    def __setstate__(self, state: dict) -> None:
        """Savegames from before the stat rework: carry the old stored numbers
        over as base values, so the player keeps what they had."""
        if "base_armor" not in state:
            old = dict(state)
            state["base_hp"] = old.get("max_hp", old.get("base_hp", 1))
            state["base_power"] = old.get("power", old.get("base_power", 0))
            state["base_armor"] = old.get("defense", old.get("base_defense", 0))
            state["main_stat"] = 0
            state["bonus_hp"] = state["bonus_stat"] = state["bonus_armor"] = 0
            state["bonus_attacks"] = max(0, old.get("attack_count", 1) - 1)
            state["bonus_mana"] = max(0, old.get("max_mana", stats.BASE_MANA) - stats.BASE_MANA)
            state["bonus_stamina"] = max(
                0, old.get("max_stamina", stats.BASE_STAMINA) - stats.BASE_STAMINA
            )
            state["mana_regen_progress"] = 0
            for gone in (
                "max_hp", "power", "defense", "base_defense", "bonus_power",
                "bonus_defense", "damage_reduction", "damage_reduction_base",
                "spell_damage_bonus", "spell_cost_reduction", "price_discount",
                "base_attack_count", "bonus_attack_count", "attack_count",
                "max_mana", "max_stamina", "base_mana",
            ):
                state.pop(gone, None)
        for added in ("bonus_mana_regen", "sprint_discount", "bonus_mass_gain", "bonus_mass_armor"):
            state.setdefault(added, 0)
        self.__dict__.update(state)

    # --- class ---

    @property
    def player_class(self):
        return getattr(getattr(self, "parent", None), "player_class", None)

    @property
    def main_stat_kind(self) -> Optional[str]:
        """STR, DEX or INT for the player, None for monsters."""
        info = stats.class_info(self.player_class)
        return info["stat"] if info else None

    def stat_of(self, kind: str) -> int:
        """The main stat if it is this kind, otherwise 0."""
        if self.main_stat_kind != kind:
            return 0
        return self.main_stat + self.bonus_stat

    @property
    def stat(self) -> int:
        return self.main_stat + self.bonus_stat if self.main_stat_kind else 0

    # --- computed stats ---

    @property
    def max_hp(self) -> int:
        return max(1, self.base_hp + self.bonus_hp)

    @property
    def gear(self):
        return getattr(getattr(self, "parent", None), "equipment", None)

    @property
    def power(self) -> int:
        gear = self.gear.power_bonus if self.gear else 0
        return (
            self.base_power
            + gear
            + self.stat_of(stats.STR) // stats.STR_DAMAGE
            + self.stat_of(stats.DEX) // stats.DEX_DAMAGE
        )

    @property
    def armor(self) -> int:
        gear = self.gear.armor_bonus if self.gear else 0
        mass_armor = 0
        if self.main_stat_kind == stats.STR:
            steps = self.mass_level // stats.MASS_ARMOR_LEVELS
            mass_armor = steps * (stats.MASS_ARMOR + self.bonus_mass_armor)
        return self.base_armor + gear + self.bonus_armor + mass_armor

    @property
    def dodge(self) -> int:
        """% chance that a melee hit misses."""
        return min(stats.DODGE_CAP, self.stat_of(stats.DEX) * stats.DEX_DODGE)

    @property
    def spell_bonus(self) -> int:
        return self.stat_of(stats.INT) // stats.INT_SPELL

    @property
    def attack_count(self) -> int:
        return 1 + self.bonus_attacks

    @property
    def max_mana(self) -> int:
        return (
            stats.BASE_MANA + self.stat_of(stats.INT) * stats.INT_MANA + self.bonus_mana
        )

    @property
    def max_stamina(self) -> int:
        return stats.BASE_STAMINA + self.bonus_stamina

    @property
    def stamina_regen(self) -> int:
        """Stamina per normal step; only the Whisperbound uses stamina."""
        if self.main_stat_kind != stats.DEX:
            return 0
        return 1 + self.stat_of(stats.DEX) // stats.DEX_STAMINA_REGEN

    @property
    def sprint_cost(self) -> int:
        return max(stats.SPRINT_COST_MIN, stats.SPRINT_COST - self.sprint_discount)

    @property
    def lunge_cost(self) -> int:
        discount = self.sprint_discount * stats.LUNGE_DISCOUNT_FACTOR
        return max(stats.SPRINT_COST_MIN, stats.LUNGE_COST - discount)

    @property
    def mana_regen_turns(self) -> int:
        turns = stats.mana_regen_turns(self.stat_of(stats.INT)) - self.bonus_mana_regen
        return max(1, turns)

    @property
    def mass_per_corpse(self) -> int:
        from_str = self.stat_of(stats.STR) // stats.STR_MASS if stats.STR_MASS else 0
        return from_str + self.bonus_mass_gain

    @property
    def mass_loss_chance(self) -> int:
        return max(
            0,
            stats.MASS_LOSS_CHANCE
            - self.mass_level
            - self.stat_of(stats.STR) // stats.STR_MASS_SAFETY,
        )

    @property
    def hp(self) -> int:
        return self._hp

    @hp.setter
    def hp(self, value: int) -> None:
        # invulnerable actors (set in the level editor) never lose HP
        if getattr(getattr(self, "parent", None), "invulnerable", False):
            value = max(value, getattr(self, "_hp", value))
        # this enshures that HP can never be negative
        # and never more than maximum
        self._hp = max(0, min(value, self.max_hp))
        if self._hp == 0 and self.parent.ai:
            self.die()

    def die(self) -> None:
        from procgen import boss_dict

        is_boss = False

        for boss in boss_dict:
            if boss_dict[boss].name == self.parent.name:
                is_boss = True

        if is_boss:
            self.perform_boss_death()

        if self.engine.player is self.parent:
            death_message = "Your flesh becomes part of the tower"
            death_message_color = color.player_die
            self.engine.scoreboard.add_score(self.engine.player.level.xp_given)
            self.engine.scoreboard.save()
        else:
            death_message = f"{self.parent.name} returns to the tower"
            death_message_color = color.enemy_die

        self.parent.char = "%"
        self.parent.color = (255, 255, 255)
        self.parent.blocks_movement = False
        self.parent.ai = None
        self.parent.name = f"remains of {self.parent.name}"
        self.parent.render_order = RenderOrder.CORPSE

        self.engine.message_log.add_message(death_message, death_message_color)
        self.engine.player.level.add_xp(self.parent.level.xp_given)

        # an item set in the level editor always drops
        drop = getattr(self.parent, "guaranteed_drop", None)
        if drop is not None and drop in self.parent.inventory.items:
            self.parent.inventory.items.remove(drop)
            drop.place(x=self.parent.x, y=self.parent.y, gamemap=self.engine.game_map)
            self.parent.guaranteed_drop = None
            self.engine.message_log.add_message(
                f"{self.parent.name.replace('remains of ', '')} dropped {drop.name}",
                color.menu_title,
            )

        signal = getattr(self.parent, "on_death", None)
        if signal:
            self.parent.on_death = None
            self.engine.game_map.fire(signal)

        # 20% chance to drop an item on death
        # drop item on death
        if random.randint(0, 100) < 20 and len(self.parent.inventory.items) > 0:
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

    def take_damage(self, amount: int, ignore_armor: Optional[bool] = False) -> int:
        """Lowers HP by amount, minus the armor's share (stats.armor_reduction).
        The fraction left is rounded randomly (1.8 -> 2 with 80%, else 1), so
        armor counts on average even against weak hits. Spells and other magic
        pass ignore_armor. Returns the damage dealt."""
        if not ignore_armor:
            reduced = amount * (1 - stats.armor_reduction(self.armor))
            amount = int(reduced) + (random.random() < reduced % 1)
        amount = max(0, amount)
        self.hp -= amount
        return amount

    def cast_spell(self, spell: Spell) -> bool:
        if self.mana >= spell.mana_cost:
            if not GENERAL_CHEATS["inf_mana"]:
                self.mana -= spell.mana_cost
            return True
        return False

    def regenerate_hp(self, in_combat: bool) -> None:
        """Once per player turn: out of combat, 1 HP every HP_REGEN_TURNS."""
        if not stats.HP_REGEN_TURNS or in_combat or self.hp >= self.max_hp:
            self.hp_regen_progress = 0
            return
        self.hp_regen_progress = getattr(self, "hp_regen_progress", 0) + 1
        if self.hp_regen_progress >= stats.HP_REGEN_TURNS:
            self.hp_regen_progress = 0
            self.hp += 1

    def regenerate(self) -> None:
        """Once per player turn: the Helixbound slowly regains mana."""
        if self.main_stat_kind != stats.INT or self.mana >= self.max_mana:
            self.mana_regen_progress = 0
            return
        self.mana_regen_progress += 1
        if self.mana_regen_progress >= self.mana_regen_turns:
            self.mana_regen_progress = 0
            self.mana = min(self.max_mana, self.mana + 1)

    def gain_mass(self, amount: int) -> int:
        """Gorebound growth; a full bar becomes a mass level, the rest carries
        over. Returns the levels gained."""
        self.mass += amount
        levels = 0
        while self.mass >= self.max_mass:
            self.mass -= self.max_mass
            self.max_mass += 10
            self.mass_level += 1
            levels += 1
        return levels

    def get_modifier_value(self, value: int) -> int:
        return math.ceil((value - 8) / 2)

    def derive_Effects(self):
        factory = ConsumptionFactory(engine=self.engine, name="Factory")
        conEffect = None
        for effect in self.current_effects:
            conEffect = factory.deriveClass(effect)
            conEffect.activate()

    def perform_boss_death(self):
        if self.parent.name == "Bloated Corpse Fly":
            death_amount = 30
            from entity_factory import corpse_fly

            self.engine.message_log.add_message(
                f"The {self.parent.name} dies and from its corpse burst {death_amount} creatures"
            )
            for i in range(death_amount):
                corpse_fly.spawn(self.engine.game_map, x=self.parent.x, y=self.parent.y)

    def reset_self(self):
        self.hp = self.max_hp
        self.mana = self.max_mana
        self.stamina = self.max_stamina
        self.mana_regen_progress = 0
        self.engine.message_log.add_message("The tower grants you respite")
