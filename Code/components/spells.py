from engine import Engine
import color

import random
import color
from typing import TYPE_CHECKING


class Spell:
    def __init__(self, engine: Engine, name: str, mana_cost: int):
        self.engine = engine
        self.name = name
        self.mana_cost = mana_cost
        self.target = None

    def activate(self):
        raise NotImplementedError()

    def get_target(self):
        consumer = self.engine.player
        self.target = None

        for actor in self.engine.game_map.actors:
            if actor is not consumer and self.engine.game_map.visible[actor.x, actor.y]:
                distance = consumer.distance(actor.x, actor.y)

                if distance < self.range:
                    self.target = actor


class LightningSpell(Spell):
    def __init__(self, engine, name, mana_cost: int):
        self.damage = 20 + self.engine.player.fighter.spell_damage_bonus
        self.range = 8
        super().__init__(engine, name, mana_cost)

    def activate(self):
        success = self.engine.player.fighter.cast_spell(self)
        if success:
            self.get_target()
            if self.target:
                living_name = self.target.name
                actual_damage = self.target.fighter.take_damage(self.damage)
                self.engine.message_log.add_message(
                    f"A bolt of lightning strikes {living_name} with a bang for {actual_damage} HP"
                )
            else:
                self.engine.message_log.add_message("No target in range", color.invalid)
        pass

    def get_target(self):
        super().get_target()


class FireballSpell(Spell):
    def __init__(self, engine, name, mana_cost: int, radius: int):
        self.damage = 12 + self.engine.player.fighter.spell_damage_bonus
        self.range = 8
        self.radius = radius
        super().__init__(engine, name, mana_cost)

    def activate(self):
        success = self.engine.player.fighter.cast_spell(self)
        if success:
            self.get_target()
            if self.target:
                for actor in self.engine.game_map.actors:
                    if actor.distance(*(self.target.x, self.target.y)) <= self.radius:
                        living_name = actor.name
                        real_damage = actor.fighter.take_damage(self.damage)
                        self.engine.message_log.add_message(
                            f"{living_name} explodes in fire taking {real_damage} HP"
                        )
                        tarets_hit = True
                if not tarets_hit:
                    self.engine.message_log.add_message(
                        "No target in range", color.invalid
                    )
            else:
                self.engine.message_log.add_message("No target in range", color.invalid)
        pass


class ConfusionSpell(Spell):
    def __init__(self, engine, name, mana_cost, number_of_turns: int):
        self.number_of_turns = number_of_turns
        self.range = 8
        super().__init__(engine, name, mana_cost)

    def activate(self):
        if self.engine.player.fighter.cast_spell(self):
            self.get_target()
            if self.target and hasattr(self.target.ai, "confused"):
                self.target.ai = self.target.ai.confused
            else:
                self.engine.message_log.add_message("Target can't be confused")
                # we need to factor in the cost reduction
                self.engine.player.fighter.mana += self.mana_cost - (
                    self.mana_cost
                    * (self.engine.player.fighter.spell_cost_reduction / 100)
                )


class SpellBook:
    def __init__(self, capacity: int):
        self.spells = []
        self.capacity = capacity

    def add_spell_to_book(self, spell: Spell):
        self.spells.append(spell)

    def learn_spell(self, spell: Spell, engine: Engine) -> bool:
        if random.randint(0, 100) >= 90 and engine.player.is_mage:
            if len(engine.player.spellbook.spells) > 0:
                for spellbook_spell in engine.player.spellbook.spells:
                    if spellbook_spell.name == spell.name:
                        return False
                self.add_spell_to_book(spell)
            else:
                self.add_spell_to_book(spell)
            engine.message_log.add_message(
                f"You're flesh learns to cast: {spell.name}", color.spell_learned
            )
            return True
        return False
