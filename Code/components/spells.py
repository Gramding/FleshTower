from engine import Engine
import color
from components.settings import PlayerClass


class Spell:
    """A spell in the player's spellbook. Damage and healing are base values;
    the caster's INT bonus is added when the spell is cast. Spells ignore armor."""

    def __init__(self, engine: Engine, name: str, mana_cost: int):
        self.engine = engine
        self.name = name
        self.mana_cost = mana_cost
        self.target = None
        self.range = 0

    def activate(self):
        raise NotImplementedError()

    @property
    def caster(self):
        return self.engine.player

    def bonus(self) -> int:
        return self.caster.fighter.spell_bonus

    def pay(self) -> bool:
        """Takes the mana; False (with a message) when there is not enough."""
        if self.caster.fighter.cast_spell(self):
            return True
        self.engine.message_log.add_message(
            f"Not enough mana for {self.name} ({self.mana_cost}).", color.invalid
        )
        return False

    def refund(self) -> None:
        fighter = self.caster.fighter
        fighter.mana = min(fighter.max_mana, fighter.mana + self.mana_cost)

    def get_target(self):
        """The nearest visible enemy within range."""
        caster = self.caster
        self.target = None
        closest = self.range
        for actor in self.engine.game_map.actors:
            if actor is caster or not self.engine.game_map.visible[actor.x, actor.y]:
                continue
            distance = caster.distance(actor.x, actor.y)
            if distance < closest:
                self.target, closest = actor, distance


class SelfSepll(Spell):
    def __init__(self, engine: Engine, name: str, mana_cost: int):
        super().__init__(engine, name, mana_cost)


class LightningSpell(Spell):
    def __init__(self, engine, name, mana_cost: int, damage: int):
        super().__init__(engine, name, mana_cost)
        self.damage = damage
        self.range = 8

    def activate(self):
        self.get_target()
        if not self.target:
            self.engine.message_log.add_message("No target in range", color.invalid)
            return
        if not self.pay():
            return
        living_name = self.target.name
        actual_damage = self.target.fighter.take_damage(self.damage + self.bonus(), True)
        self.engine.message_log.add_message(
            f"A bolt of lightning strikes {living_name} with a bang for {actual_damage} HP"
        )


class FireballSpell(Spell):
    def __init__(self, engine, name, mana_cost: int, radius: int):
        super().__init__(engine, name, mana_cost)
        self.damage = 12
        self.range = 8
        self.radius = radius

    def activate(self):
        self.get_target()
        if not self.target:
            self.engine.message_log.add_message("No target in range", color.invalid)
            return
        if not self.pay():
            return
        center = (self.target.x, self.target.y)
        for actor in list(self.engine.game_map.actors):
            if actor is self.caster or actor.distance(*center) > self.radius:
                continue
            living_name = actor.name
            real_damage = actor.fighter.take_damage(self.damage + self.bonus(), True)
            self.engine.message_log.add_message(
                f"{living_name} explodes in fire taking {real_damage} HP"
            )


class ConfusionSpell(Spell):
    def __init__(self, engine, name, mana_cost, number_of_turns: int):
        self.number_of_turns = number_of_turns
        super().__init__(engine, name, mana_cost)
        self.range = 8

    def activate(self):
        self.get_target()
        if not (self.target and hasattr(self.target.ai, "confused")):
            self.engine.message_log.add_message("Target can't be confused")
            return
        if self.pay():
            self.target.ai = self.target.ai.confused


class HealingSpell(SelfSepll):
    def __init__(self, engine: Engine, name: str, mana_cost: int, healing: int):
        self.healing = healing
        super().__init__(engine, name, mana_cost)

    def activate(self):
        if self.pay():
            healed = self.caster.fighter.heal(self.healing + self.bonus())
            self.engine.message_log.add_message(
                f"You recover {healed} HP", color.health_recovered
            )


class SpellBook:
    def __init__(self, capacity: int):
        self.spells = []
        self.capacity = capacity

    def add_spell_to_book(self, spell: Spell):
        self.spells.append(spell)

    def learn_spell(self, spell: Spell, engine: Engine) -> bool:
        if engine.player.player_class == PlayerClass.MAGE:
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
