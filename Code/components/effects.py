from __future__ import annotations
from components.affix import PercentHPIncrease
from components.settings import PlayerClass
from components import stats
from typing import TYPE_CHECKING, Optional
import color
from components.spells import (
    LightningSpell,
    FireballSpell,
    ConfusionSpell,
    HealingSpell,
)

import random

if TYPE_CHECKING:
    from engine import Engine
    from entity import Entity


class LogBook:
    def __init__(self):
        self.book: dict[Entity:int] = {}
        pass

    def write_to_book(self, entity_name: str):
        if entity_name in self.book:
            self.book[entity_name] += 1
        else:
            self.book[entity_name] = 1


class Effect:
    def __init__(self):
        pass

    def activate(
        self,
        engine: Engine,
        corpse: Entity,
        first: bool = False,
    ):
        engine.player.logbook.write_to_book(entity_name=corpse.name[:30])
        if engine.player.player_class == PlayerClass.FIGHTER:
            fighter = engine.player.fighter
            # Rebalance the amount of mass gained
            increase = random.randint(1, 15) + fighter.mass_per_corpse
            if fighter.gain_mass(increase):
                engine.message_log.add_message(
                    f"Your mass grows to level {fighter.mass_level}. Your flesh hardens.",
                    color.corpse_consumption,
                )

        if first:
            engine.message_log.add_message(
                f"You consume {corpse.name}",
                color.corpse_consumption,
            )
        else:
            engine.message_log.add_message(
                f"You consume {corpse.name}, nothing happens",
                color.corpse_consumption,
            )
        if corpse in engine.game_map.entities:
            engine.game_map.entities.remove(corpse)
        engine.player.fighter.derive_Effects()

    def add_currency(self, engine: Engine, amount: int):
        if amount != 0:
            engine.message_log.add_message(f"You find {amount} organs")
            engine.player.currency += amount


class DefaultEffect(Effect):
    def __init__(self):
        super().__init__()

    def activate(self, engine, corpse, first=False):
        self.add_currency(engine=engine, amount=random.randint(0, 3))
        return super().activate(engine, corpse, False)


class OrcEffect(Effect):
    def __init__(self):
        super().__init__()

    def activate(
        self,
        engine,
        corpse,
        first=False,
    ):
        # If player eats an orc health increses by one
        if corpse.name not in engine.player.logbook.book:
            super().activate(engine, corpse, True)
        else:
            super().activate(engine, corpse, False)
        self.add_currency(engine, random.randint(3, 5))
        engine.affixManager.gain_affix(PercentHPIncrease(0.01))


class TrollEffect(Effect):
    def __init__(self):
        super().__init__()

    def activate(
        self,
        engine,
        corpse,
        first=False,
    ):
        if corpse.name not in engine.player.logbook.book:
            super().activate(engine, corpse, True)
        else:
            super().activate(engine, corpse, False)
        self.add_currency(engine, random.randint(3, 5))


class Lvl5BossEffect(Effect):
    """The Weak Mage boss: a Helixbound learns its lightning bolt."""

    def __init__(self):
        super().__init__()

    def activate(
        self,
        engine,
        corpse,
        first=False,
    ):
        learned = engine.player.spellbook.learn_spell(
            spell=LightningSpell(
                engine=engine, name="Lightning Bolt I", mana_cost=stats.STARTER_SPELL_COST, damage=5
            ),
            engine=engine,
        )
        super().activate(engine, corpse, learned)
        self.add_currency(engine, random.randint(3, 5))


def choose_class(engine: Engine, corpse: Entity, player_class, other_corpse: str) -> bool:
    """Eating a class corpse in the start room picks the class, once."""
    from components.stats import class_info

    player = engine.player
    if player.class_chosen:
        return False
    for entity in list(engine.game_map.entities):
        if other_corpse in entity.name:
            engine.game_map.entities.remove(entity)
    info = class_info(player_class)
    player.player_class = player_class
    player.class_chosen = True
    fighter = player.fighter
    fighter.base_hp += info["hp"]
    fighter.hp = fighter.max_hp
    fighter.mana = fighter.max_mana
    fighter.stamina = fighter.max_stamina
    engine.message_log.add_message(f"You are {info['name']} now.", color.mage)
    return True


class HelixboundEffect(Effect):
    """The blue class corpse of the start room."""

    def __init__(self):
        super().__init__()

    def activate(self, engine, corpse, first=False):
        chosen = choose_class(engine, corpse, PlayerClass.MAGE, "Gore")
        if chosen:
            engine.message_log.add_message(
                "You feel the mutagen of the mage coursing through your blood. Your flesh weakens but your mind strengthens",
                color.mage,
            )
            engine.player.spellbook.learn_spell(
                spell=LightningSpell(
                    engine=engine, name="Lightning Bolt I", mana_cost=stats.STARTER_SPELL_COST, damage=5
                ),
                engine=engine,
            )
        return super().activate(engine, corpse, chosen)


class LightningEffect(Effect):
    def __init__(self):
        super().__init__()

    def activate(
        self,
        engine,
        corpse,
        first=False,
    ):
        spell_name = "Lightning Spell"
        success = engine.player.spellbook.learn_spell(
            spell=LightningSpell(
                engine=engine, name=spell_name, mana_cost=10, damage=20
            ),
            engine=engine,
        )

        return super().activate(engine, corpse, success)


class FireballEffect(Effect):
    def __init__(self):
        super().__init__()

    def activate(
        self,
        engine,
        corpse,
        first=False,
    ):
        spell_name = "Fireball Spell"
        success = engine.player.spellbook.learn_spell(
            spell=FireballSpell(engine, spell_name, 10, 3), engine=engine
        )
        return super().activate(engine, corpse, success)


class ConfusionEffect(Effect):
    def __init__(self):
        super().__init__()

    def activate(
        self,
        engine,
        corpse,
        first=False,
    ):
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


class HealingScrollEffect(Effect):
    def __init__(self, spellName: str = "", mana_cost: int = 0, healing: int = 0):
        self.spellName = spellName
        self.mana_cost = mana_cost
        self.healing = healing
        super().__init__()

    def activate(
        self,
        engine: Engine,
        corpse: Entity,
        first: bool = False,
    ):
        success = engine.player.spellbook.learn_spell(
            spell=HealingSpell(
                engine=engine,
                name=self.spellName,
                mana_cost=self.mana_cost,
                healing=self.healing,
            ),
            engine=engine,
        )
        return super().activate(engine, corpse, success)


class HealthEffect(Effect):
    def __init__(self):
        super().__init__()

    def activate(
        self,
        engine,
        corpse,
        first=False,
    ):
        heal_amount = int(
            engine.player.fighter.max_hp * (corpse.consumable.amount / 100)
        )
        engine.player.fighter.heal(heal_amount)
        engine.message_log.add_message(f"You gain {heal_amount} HP")
        super().activate(engine, corpse, True)


class ManaEffect(Effect):
    def __init__(self):
        super().__init__()

    def activate(
        self,
        engine,
        corpse,
        first=False,
    ):
        if engine.player.player_class == PlayerClass.MAGE:
            engine.player.fighter.heal_mana(corpse.consumable.amount)
            engine.message_log.add_message(f"You gain {corpse.consumable.amount} Mana")
            return super().activate(engine, corpse, True)
        else:
            return super().activate(engine, corpse, False)


class SwordEffect(Effect):
    def __init__(self):
        super().__init__()

    def activate(
        self,
        engine,
        corpse,
        first=False,
    ):
        if corpse.name not in engine.player.logbook.book:
            super().activate(engine, corpse, True)
        else:
            super().activate(engine, corpse, False)


class DaggerEffect(Effect):
    def __init__(self):
        super().__init__()

    def activate(
        self,
        engine,
        corpse,
        first=False,
    ):
        if corpse.name not in engine.player.logbook.book:
            super().activate(engine, corpse, True)
        else:
            super().activate(engine, corpse, False)


class LeatherArmorEffect(Effect):
    def __init__(self):
        super().__init__()

    def activate(
        self,
        engine,
        corpse,
        first=False,
    ):
        if corpse.name not in engine.player.logbook.book:
            super().activate(engine, corpse, True)
        else:
            super().activate(engine, corpse, False)


class ChainMailEffect(Effect):
    def __init__(self):
        super().__init__()

    def activate(
        self,
        engine,
        corpse,
        first=False,
    ):
        if corpse.name not in engine.player.logbook.book:
            super().activate(engine, corpse, True)
        else:
            super().activate(engine, corpse, False)


class GoreboundEffect(Effect):
    """The red class corpse of the start room."""

    def __init__(self):
        super().__init__()

    def activate(
        self,
        engine,
        corpse,
        first=False,
    ):
        chosen = choose_class(engine, corpse, PlayerClass.FIGHTER, "Helix")
        return super().activate(engine, corpse, chosen)


class FleshGolemEffect(Effect):
    def __init__(self):
        super().__init__()

    def activate(
        self,
        engine,
        corpse,
        first=False,
    ):
        if corpse.name not in engine.player.logbook.book:
            first = True
            engine.player.fighter.bonus_attacks += 1
            engine.player.fighter.base_hp *= 2
        return super().activate(engine, corpse, first)


class ZombieEffect(Effect):
    def __init__(self):
        super().__init__()

    def activate(
        self,
        engine,
        corpse,
        first=False,
    ):
        if corpse.name not in engine.player.logbook.book:
            engine.player.fighter.current_effects.append("Zombie")
            first = True
        return super().activate(engine, corpse, first)


class FlayedThrall(Effect):
    def __init__(self):
        super().__init__()

    def activate(
        self,
        engine,
        corpse,
        first=False,
    ):
        if corpse.name not in engine.player.logbook.book:
            engine.player.fighter.current_effects.append("FlayedThrall")
            first = True
        return super().activate(engine, corpse, first)


# Effects for Bosses BossEffects


class BossEffect(Effect):
    def __init__(self):
        super().__init__()

    def activate(
        self,
        engine,
        corpse,
        first=False,
    ):
        if corpse.name not in engine.player.logbook.book:
            first = True
        from procgen import generate_boss_room_empty

        engine.message_log.add_message(
            f"From consuming the strange flesh of the {corpse.name} your vision fades for a second"
        )

        engine.game_map = generate_boss_room_empty(
            engine=engine,
            map_width=engine.game_world.map_width,
            map_height=engine.game_world.map_height,
            current_floor=engine.game_world.current_floor,
            current_x=engine.player.x,
            current_y=engine.player.y,
        )
        return super().activate(engine, corpse, first)


class ViceraAbominationEffect(BossEffect):
    def __init__(self):
        super().__init__()

    def activate(self, engine, corpse, first=False):
        return super().activate(engine, corpse, first)


class BloatedCorpseFlyEffect(BossEffect):
    def __init__(self):
        super().__init__()

    def activate(self, engine, corpse, first=False):
        return super().activate(engine, corpse, first)
