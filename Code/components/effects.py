from __future__ import annotations

from typing import Optional, Tuple, TYPE_CHECKING, Dict
import color
import random
from components.spells import LightningSpell, FireballSpell

if TYPE_CHECKING:
    from engine import Engine
    from entity import Entity


class Effect:
    def __init__(self):
        pass

    def activate(self, engine: Engine, corpse: Entity, first: bool):
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
        if engine.player.number_of_orcs_consumed < 1:
            super().activate(engine, corpse, True)
            engine.player.level.increase_max_hp(1)
            engine.player.number_of_orcs_consumed += 1
        else:
            super().activate(engine, corpse, False)
            engine.player.number_of_orcs_consumed += 1


class TrollEffect(Effect):
    def __init__(self):
        super().__init__()

    def activate(self, engine, corpse):
        if engine.player.number_of_trolls_consumed < 1:
            super().activate(engine, corpse, True)
            engine.player.level.increase_power(1)
            engine.player.number_of_trolls_consumed += 1
        else:
            super().activate(engine, corpse, False)
            engine.player.number_of_trolls_consumed += 1


class Lvl5BossEffect(Effect):
    def __init__(self):
        super().__init__()

    def activate(self, engine: Engine, corpse):
        if engine.player.number_of_weak_mages_consumed < 1:
            super().activate(engine, corpse, True)
            # TODO Implement the effect for consuming a mage
            engine.player.is_mage = True
            engine.player.fighter.mana = 20
            engine.player.fighter.max_mana = 20
            engine.player.fighter.max_hp = int(engine.player.fighter.max_hp / 2)
            engine.player.fighter.hp = int(engine.player.fighter.hp / 2)
            engine.message_log.add_message(
                f"You feel the mana of the mage coursing through your blood. Your flesh weakens but your mind strengthens",
                color.mage,
            )
            engine.player.number_of_weak_mages_consumed += 1
        else:
            super().activate(engine, corpse, False)
            engine.player.number_of_weak_mages_consumed += 1


class LightningEffect(Effect):
    def __init__(self):
        super().__init__()

    def activate(self, engine: Engine, corpse: Entity):
        engine.player.number_of_scrolls_of_lightning_consumed += 1
        if random.randint(0, 10000000) > 90 and engine.player.is_mage:
            if len(engine.player.spellbook.spells) > 0:
                for spell in engine.player.spellbook.spells:
                    if spell.name == "Lightning Spell":
                        return super().activate(engine, corpse, False)
                    else:
                        engine.player.spellbook.add_spell_to_book(
                            spell=LightningSpell(engine, "Lightning Spell", 10)
                        )
            else:
                engine.player.spellbook.add_spell_to_book(
                    spell=LightningSpell(engine, "Lightning Spell", 10)
                )
            engine.message_log.add_message(
                f"You're flesh learns to cast: Lightning Spell", color.spell_learned
            )
            return super().activate(engine, corpse, True)
        return super().activate(engine, corpse, False)


class FireballEffect(Effect):
    def __init__(self):
        super().__init__()

    def activate(self, engine: Engine, corpse):
        engine.player.number_of_scrolls_of_fireball_consumed += 1
        spell_name = "Fireball Spell"
        if random.randint(0, 10000000) > 90 and engine.player.is_mage:
            if len(engine.player.spellbook.spells) > 0:
                for spell in engine.player.spellbook.spells:
                    if spell.name == spell_name:
                        return super().activate(engine, corpse, False)
                    else:
                        engine.player.spellbook.add_spell_to_book(
                            spell=FireballSpell(engine, spell_name, 10, 3)
                        )
            else:
                engine.player.spellbook.add_spell_to_book(
                    spell=FireballSpell(engine, spell_name, 10, 3)
                )
            engine.message_log.add_message(
                f"You're flesh learns to cast: {spell_name}", color.spell_learned
            )
            return super().activate(engine, corpse, True)
        return super().activate(engine, corpse, False)


class ConfusionEffect(Effect):
    def __init__(self):
        super().__init__()

    def activate(self, engine: Engine, corpse):
        engine.player.number_of_scrolls_of_confusion_consumed += 1
        return super().activate(engine, corpse, True)


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

    def activate(self, engine, corpse, first):
        if engine.player.number_of_swords_consumed < 1:
            super().activate(engine, corpse, True)
            engine.player.level.increase_power(1)
            engine.player.number_of_swords_consumed += 1
        else:
            super().activate(engine, corpse, False)
            engine.player.number_of_swords_consumed += 1
