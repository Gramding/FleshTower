from __future__ import annotations

from typing import Optional, Tuple, TYPE_CHECKING, Dict
import color
from components.spells import LightningSpell, FireballSpell, ConfusionSpell, SpellBook

if TYPE_CHECKING:
    from engine import Engine
    from entity import Entity


class Effect:
    def __init__(self):
        pass

    def activate(self, engine: Engine, corpse: Entity, first: bool):
        engine.player.logbook.write_to_book(entity_name=corpse.name)
        if first:
            engine.message_log.add_message(
                f"You bury you're teeth in {corpse.name}",
                color.corpse_consumption,
            )
            engine.game_map.entities.remove(corpse)
        else:
            engine.message_log.add_message(
                f"You bury you're teeth in {corpse.name}, nothing happens",
                color.corpse_consumption,
            )
            engine.game_map.entities.remove(corpse)


class OrcEffect(Effect):
    def __init__(self):
        super().__init__()

    def activate(self, engine: Engine, corpse: Entity):
        # If player eats an orc health increses by one
        if corpse.name not in engine.player.logbook.book:
            super().activate(engine, corpse, True)
            engine.player.level.increase_max_hp(1, False)
        else:
            super().activate(engine, corpse, False)


class RatEffect(Effect):
    def __init__(self):
        super().__init__()

    def activate(self, engine, corpse):
        return super().activate(engine, corpse, False)


class TrollEffect(Effect):
    def __init__(self):
        super().__init__()

    def activate(self, engine, corpse):
        if corpse.name not in engine.player.logbook.book:
            super().activate(engine, corpse, True)
            engine.player.level.increase_power(1, False)
        else:
            super().activate(engine, corpse, False)


class Lvl5BossEffect(Effect):
    def __init__(self):
        super().__init__()

    def activate(self, engine: Engine, corpse):
        if corpse.name not in engine.player.logbook.book:
            super().activate(engine, corpse, True)
            # TODO Implement the effect for consuming a mage
            engine.player.is_mage = True
            engine.player.fighter.mana = 30
            engine.player.fighter.max_mana = 30
            engine.player.fighter.max_hp = 20
            engine.player.fighter.hp = 20
            engine.message_log.add_message(
                f"You feel the mana of the mage coursing through your blood. Your flesh weakens but your mind strengthens",
                color.mage,
            )
        else:
            super().activate(engine, corpse, False)


class LightningEffect(Effect):
    def __init__(self):
        super().__init__()

    def activate(self, engine: Engine, corpse: Entity):
        spell_name = "Lightning Spell"
        success = engine.player.spellbook.learn_spell(
            spell=LightningSpell(engine, spell_name, 10), engine=engine
        )

        return super().activate(engine, corpse, success)


class FireballEffect(Effect):
    def __init__(self):
        super().__init__()

    def activate(self, engine: Engine, corpse):
        spell_name = "Fireball Spell"
        success = engine.player.spellbook.learn_spell(
            spell=FireballSpell(engine, spell_name, 10, 3), engine=engine
        )
        return super().activate(engine, corpse, success)


class ConfusionEffect(Effect):
    def __init__(self):
        super().__init__()

    def activate(self, engine: Engine, corpse):
        spell_name = "Confusion Spell"
        success = engine.player.spellbook.learn_spell(
            spell=ConfusionSpell(
                engine,
                spell_name,
                5,
                10,
            ),
            engine=engine,
        )
        return super().activate(engine, corpse, success)


class HealthEffect(Effect):
    def __init__(self):
        super().__init__()

    def activate(self, engine: Engine, corpse):
        engine.player.fighter.heal(corpse.consumable.amount)
        engine.message_log.add_message(f"You gain {corpse.consumable.amount} HP")
        super().activate(engine, corpse, True)


class ManaEffect(Effect):
    def __init__(self):
        super().__init__()

    def activate(self, engine: Engine, corpse):
        if engine.player.is_mage:
            engine.player.fighter.heal_mana(corpse.consumable.amount)
            engine.message_log.add_message(f"You gain {corpse.consumable.amount} Mana")
            return super().activate(engine, corpse, True)
        else:
            return super().activate(engine, corpse, False)


class SwordEffect(Effect):
    def __init__(self):
        super().__init__()

    def activate(self, engine, corpse):
        if corpse.name not in engine.player.logbook.book:
            super().activate(engine, corpse, True)
            engine.player.level.increase_power(1, False)
        else:
            super().activate(engine, corpse, False)


class DaggerEffect(Effect):
    def __init__(self):
        super().__init__()

    def activate(self, engine, corpse):
        if corpse.name not in engine.player.logbook.book:
            super().activate(engine, corpse, True)
            engine.player.level.increase_power(1, False)
        else:
            super().activate(engine, corpse, False)


class LeatherArmorEffect(Effect):
    def __init__(self):
        super().__init__()

    def activate(self, engine, corpse):
        if corpse.name not in engine.player.logbook.book:
            super().activate(engine, corpse, True)
            engine.player.level.increase_defense(1, False)
        else:
            super().activate(engine, corpse, False)


class ChainMailEffect(Effect):
    def __init__(self):
        super().__init__()

    def activate(self, engine, corpse):
        if corpse.name not in engine.player.logbook.book:
            super().activate(engine, corpse, True)
            engine.player.level.increase_defense(1, False)
        else:
            super().activate(engine, corpse, False)


class LogBook:
    def __init__(self):
        self.book: dict[Entity:int] = {}
        pass

    def write_to_book(self, entity_name: str):
        if entity_name in self.book:
            self.book[entity_name] += 1
        else:
            self.book[entity_name] = 1
