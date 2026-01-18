from __future__ import annotations

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
        if engine.player.is_fighter:
            increase = random.randint(1, 15)  # Rebalance the amount of mass gained
            # increas player mass level
            if engine.player.fighter.mass + increase <= engine.player.fighter.max_mass:
                engine.player.fighter.mass += increase
            else:
                engine.player.fighter.mass = 0
                engine.player.fighter.max_mass += 10
                engine.player.fighter.mass_level += 1

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
    def __init__(self):
        super().__init__()

    def activate(
        self,
        engine,
        corpse,
        first=False,
    ):
        gorebound = ""
        for entity in engine.game_map.entities:
            if "Gore" in entity.name:
                gorebound = entity
        if gorebound != "":
            engine.game_map.entities.remove(gorebound)
        if corpse.name not in engine.player.logbook.book:
            super().activate(engine, corpse, False)
            engine.player.is_mage = True
            engine.player.is_rouge = False
            engine.player.fighter.base_hp = 20
            engine.player.fighter.hp = 20
            engine.message_log.add_message(
                "You feel the mutagen of the mage coursing through your blood. Your flesh weakens but your mind strengthens",
                color.mage,
            )
            engine.player.spellbook.learn_spell(
                spell=LightningSpell(
                    engine=engine, name="Lightning Bolt I", mana_cost=2, damage=5
                ),
                engine=engine,
            )
        else:
            super().activate(engine, corpse, False)
        self.add_currency(engine, random.randint(3, 5))


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
        if engine.player.is_mage:
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
    def __init__(self):
        super().__init__()

    def activate(
        self,
        engine,
        corpse,
        first=False,
    ):
        helixbound = ""
        for entity in engine.game_map.entities:
            if "Helix" in entity.name:
                helixbound = entity
        if helixbound:
            engine.game_map.entities.remove(helixbound)
            engine.player.is_fighter = True
            engine.player.is_rouge = False
            engine.player.fighter.base_hp = 40
            engine.player.fighter.hp = 40
        return super().activate(engine, corpse, True)


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
            engine.player.fighter.bonus_attack_count += 1
            engine.player.is_mage = False
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
