from __future__ import annotations

from typing import Optional, Tuple, TYPE_CHECKING, Dict
import color
import exceptions

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

    def activate(self, engine, corpse, first):
        if engine.player.number_of_trolls_consumed < 1:
            super().activate(engine, corpse, True)
            engine.player.level.increase_power(1)
            engine.player.number_of_trolls_consumed += 1
        else:
            super().activate(engine, corpse, False)
            engine.player.number_of_trolls_consumed += 1
