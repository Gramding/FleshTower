from __future__ import annotations

from typing import Optional, Tuple, TYPE_CHECKING, Dict
import color
import exceptions
import random

if TYPE_CHECKING:
    from engine import Engine
    from entity import Actor, Entity, Item


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

    def activate(self, engine, corpse):
        if engine.player.number_of_weak_mages_consumed < 1:
            super().activate(engine, corpse, True)
            # TODO Implement the effect for consuming a mage
            engine.player.is_mage = True
            engine.player.fighter.mana = 20
            engine.player.fighter.max_mana = 20
            engine.message_log.add_message(
                f"You now feel mana coursing through your blood",
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
        if engine.player.is_mage:
            if random.randint(0, 100) > 90:
                # TODO Learn the spell
                pass

        return super().activate(engine, corpse)


class HealthEffect(Effect):
    def __init__(self):
        super().__init__()

    def activate(self, engine, corpse):
        engine.player.fighter.heal(corpse.consumable.amount)
        engine.message_log.add_meassage(f"You gain {corpse.consumable.amount} HP")
        super().activate(engine, corpse, True)
