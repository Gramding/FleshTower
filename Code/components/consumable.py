from __future__ import annotations

from typing import Optional, TYPE_CHECKING

import actions
import color
import components.ai
import components.inventory
from components.base_component import BaseComponent
from exceptions import Impossible
from input_handlers import (
    SingleRangedAttackHandler,
    AreaRangedAttackHandler,
    ActionOrHandler,
)

if TYPE_CHECKING:
    from entity import Actor, Item


class Consumable(BaseComponent):
    parent: Item

    def get_action(self, consumer: Actor) -> Optional[ActionOrHandler]:
        return actions.ItemAction(consumer, self.parent)

    def activate(self, action: actions.ItemAction) -> None:
        raise NotImplementedError()

    def consume(self) -> None:
        entity = self.parent
        inventory = entity.parent
        if isinstance(inventory, components.inventory.Inventory):
            inventory.items.remove(entity)


class HealingConsumable(Consumable):
    def __init__(self, amount: int):
        # amount in % of player health
        self.amount = amount

    def activate(self, action: actions.ItemAction) -> None:
        consumer = action.entity
        # percent based healing
        heal_amount = int(self.engine.player.fighter.max_hp * (self.amount / 100))
        amount_recovered = consumer.fighter.heal(heal_amount)

        if amount_recovered > 0:
            self.engine.message_log.add_message(
                f"You drink a {self.parent.name}, and recover {amount_recovered} HP!",
                color.health_recovered,
            )
            self.consume()
            consumer.logbook.write_to_book(self.parent.name)
        else:
            raise Impossible(f"Your HP is already full!")


class FireballDamageConsumable(Consumable):
    def __init__(self, damage: int, radius: int):
        self.damage = damage
        self.radius = radius

    def get_action(self, consumer) -> AreaRangedAttackHandler:
        self.engine.message_log.add_message("Select target area", color.needs_target)
        return AreaRangedAttackHandler(
            self.engine,
            radius=self.radius,
            callback=lambda xy: actions.ItemAction(consumer, self.parent, xy),
        )

    def activate(self, action):
        target_xy = action.target_xy
        if not self.engine.game_map.visible[target_xy]:
            raise Impossible("Area not Visible")

        tarets_hit = False

        for actor in self.engine.game_map.actors:
            if actor.distance(*target_xy) <= self.radius:
                living_name = actor.name
                real_damage = actor.fighter.take_damage(self.damage)
                self.engine.message_log.add_message(
                    f"{living_name} explodes in fire taking {real_damage} HP"
                )
                tarets_hit = True
        if not tarets_hit:
            raise Impossible("No targets in radius")
        self.consume()


class LightningDamageConsumable(Consumable):
    def __init__(self, damage: int, maximum_range: int):
        self.damage = damage
        self.maximum_range = maximum_range
        self.fuck_around_find_out = 0

    def activate(
        self, action: actions.ItemAction, is_npc: Optional[bool] = False
    ) -> None:
        consumer = action.entity
        target = None
        closest_distance = self.maximum_range + 1.0

        for actor in self.engine.game_map.actors:
            if actor is not consumer and self.parent.gamemap.visible[actor.x, actor.y]:
                distance = consumer.distance(actor.x, actor.y)

                if distance < closest_distance:
                    target = actor
                    closest_distance = distance

        if target:
            living_name = actor.name
            actual_damage = target.fighter.take_damage(self.damage)
            self.engine.message_log.add_message(
                f"A bolt of lightning strikes {living_name} with a bang for {actual_damage} HP"
            )
            if not is_npc:
                self.consume()
        else:
            self.fuck_around_find_out += 1
            if self.fuck_around_find_out > 3:
                actual_damage = consumer.fighter.take_damage(self.damage)
                self.consume()
                self.fuck_around_find_out = 0
                raise Impossible(
                    f"You were the only target and took {actual_damage} HP"
                )
            raise Impossible("No enemy in range")


class ConfusionConsumable(Consumable):
    def __init__(self, number_of_turns: int):
        self.number_of_turns = number_of_turns

    def get_action(self, consumer) -> SingleRangedAttackHandler:
        self.engine.message_log.add_message("Slect a target", color.needs_target)
        return SingleRangedAttackHandler(
            self.engine,
            callback=lambda xy: actions.ItemAction(consumer, self.parent, xy),
        )

    def activate(self, action):
        consumer = action.entity
        target = action.target_actor

        if not self.engine.game_map.visible[action.target_xy]:
            raise Impossible("Target not visible")
        if not target:
            raise Impossible("Select enemy target")
        if target is consumer:
            raise Impossible("Are you already confused?")
        self.engine.message_log.add_message(f"{target.name} stumbels around aimlessly")
        target.ai = components.ai.ConfusedEnemy(
            entity=target,
            previous_ai=target.ai,
            turns_remaining=self.number_of_turns,
        )
        self.consume()


class ManaConsumable(Consumable):
    def __init__(self, amount: int):
        self.amount = amount
        super().__init__()

    def activate(self, action: actions.ItemAction) -> None:
        consumer = action.entity
        amount_recovered = consumer.fighter.heal_mana(self.amount)
        if self.engine.player.is_mage:
            if amount_recovered > 0:
                self.engine.message_log.add_message(
                    f"You drink a {self.parent.name}, and recover {amount_recovered} Mana!",
                    color.mana_bar_filled,
                )
                self.consume()
                consumer.logbook.write_to_book(self.parent.name)
            else:
                raise Impossible(f"Your Mana is already full!")
        else:
            raise Impossible("The blue liquid has no effect on you")
