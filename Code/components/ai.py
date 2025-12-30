from __future__ import annotations

import random

from typing import List, Optional, Tuple, TYPE_CHECKING

import numpy as np
import tcod

from actions import (
    Action,
    MeleeAction,
    MovementAction,
    WaitAction,
    BumpAction,
)


if TYPE_CHECKING:
    from entity import Actor


class BaseAI(Action):
    def perform(self) -> None:
        raise NotImplementedError()

    def get_path_to(self, dest_x: int, dest_y: int) -> list[Tuple[int, int]]:
        cost = np.array(self.entity.gamemap.tiles["walkable"], dtype=np.int8)
        for entity in self.entity.gamemap.entities:
            if entity.blocks_movement and cost[entity.x, entity.y]:
                cost[entity.x, entity.y] += 10

        graph = tcod.path.SimpleGraph(cost=cost, cardinal=2, diagonal=2)
        pathfinder = tcod.path.Pathfinder(graph)
        pathfinder.add_root((self.entity.x, self.entity.y))

        path: List[List[int]] = pathfinder.path_to((dest_x, dest_y))[1:].tolist()
        return [(index[0], index[1]) for index in path]


class ConfusedEnemy(BaseAI):
    def __init__(self, entity, previous_ai: Optional[BaseAI], turns_remaining):
        super().__init__(entity)
        self.previous_ai = previous_ai
        self.turns_remaining = turns_remaining

    def perform(self):
        if self.turns_remaining <= 0:
            self.engine.message_log.add_message(
                f"{self.entity.name} is no longer confused"
            )
            self.entity.ai = self.previous_ai
        else:
            direction_x, direction_y = random.choice([
                (-1, -1),  # Northwest
                (0, -1),  # North
                (1, -1),  # Northeast
                (-1, 0),  # West
                (1, 0),  # East
                (-1, 1),  # Southwest
                (0, 1),  # South
                (1, 1),  # Southeast
            ])
            self.turns_remaining -= 1
            return BumpAction(self.entity, direction_x, direction_y).perform()


class HostileEnemy(BaseAI):
    def __init__(self, entity: Actor):
        super().__init__(entity)
        self.path: List[Tuple[int, int]] = []
        self.confused = ConfusedEnemy(entity, self, 8)

    def perform(self) -> None:
        target = self.engine.player
        dx = target.x - self.entity.x
        dy = target.y - self.entity.y
        distance = max(abs(dx), abs(dy))

        if self.engine.game_map.visible[self.entity.x, self.entity.y]:
            if distance <= 1:
                return MeleeAction(self.entity, dx, dy).perform()
            self.path = self.get_path_to(target.x, target.y)

        if self.path:
            dest_x, dest_y = self.path.pop(0)
            return MovementAction(
                self.entity,
                dest_x - self.entity.x,
                dest_y - self.entity.y,
            ).perform()

        return WaitAction(self.entity).perform()


class HostileCaster(BaseAI):
    def __init__(self, entity):
        super().__init__(entity)
        self.path: List[Tuple[int, int]] = []
        self.spell_slots = 2

    def perform(self):
        target = self.engine.player
        dx = target.x - self.entity.x
        dy = target.y - self.entity.y
        closest_distance = 10
        distance = max(abs(dx), abs(dy))
        for actor in self.engine.game_map.actors:
            if (
                actor.x != self.entity.x and actor.y != self.entity.y
            ) and self.engine.game_map.visible[actor.x, actor.y]:
                distance = self.entity.distance(actor.x, actor.y)

                if distance < closest_distance:
                    target = actor
                    closest_distance = distance
        if (
            distance < 10
            and distance > 4
            and self.spell_slots > 0
            and self.engine.game_map.visible[target.x, target.y]
        ):
            self.spell_slots -= 1
            # Caster ignores defence
            actual_damage = target.fighter.take_damage(8, True)
            self.engine.message_log.add_message(
                f"{self.entity.name} stikes you for {actual_damage} HP"
            )
        else:
            if self.engine.game_map.visible[self.entity.x, self.entity.y]:
                if distance <= 1:
                    return MeleeAction(self.entity, dx, dy).perform()
                self.path = self.get_path_to(target.x, target.y)

            if self.path:
                dest_x, dest_y = self.path.pop(0)
                return MovementAction(
                    self.entity,
                    dest_x - self.entity.x + 1,
                    dest_y - self.entity.y + 1,
                ).perform()


class Vendor(BaseAI):
    def __init__(self, entity):
        super().__init__(entity)

    def perform(self):
        return WaitAction(self.entity).perform()


class ViceraAbomination(BaseAI):
    def __init__(self, entity: Actor) -> None:
        super().__init__(entity)
        self.turn_count = 0
        self.path: List[Tuple[int, int]] = []
        self.confused = ConfusedEnemy(entity, self, 8)

    def perform(self) -> None:
        target = self.engine.player
        dx = target.x - self.entity.x
        dy = target.y - self.entity.y
        distance = max(abs(dx), abs(dy))

        if self.turn_count >= 10:
            self.turn_count = 0
            from entity_factory import vicera_spawn

            vicera_spawn.spawn(self.engine.game_map, self.entity.x, self.entity.y)
        else:
            self.turn_count += 1

        if self.engine.game_map.visible[self.entity.x, self.entity.y]:
            if distance <= 1:
                return MeleeAction(self.entity, dx, dy).perform()
            self.path = self.get_path_to(target.x, target.y)

        if self.path:
            dest_x, dest_y = self.path.pop(0)
            return MovementAction(
                self.entity,
                dest_x - self.entity.x,
                dest_y - self.entity.y,
            ).perform()

        return WaitAction(self.entity).perform()


class BloatedCorpseFly(BaseAI):
    def __init__(self, entity: Actor) -> None:
        super().__init__(entity)
        self.turn_count = 0
        self.path: List[Tuple[int, int]] = []
        self.confused = ConfusedEnemy(entity, self, 8)

    def perform(self) -> None:
        target = self.engine.player
        dx = target.x - self.entity.x
        dy = target.y - self.entity.y
        distance = max(abs(dx), abs(dy))

        # TODO implement special AI feature for the floor 10 boss

        if self.engine.game_map.visible[self.entity.x, self.entity.y]:
            if distance <= 1:
                return MeleeAction(self.entity, dx, dy).perform()
            self.path = self.get_path_to(target.x, target.y)

        if self.path:
            dest_x, dest_y = self.path.pop(1)
            return MovementAction(
                self.entity,
                dest_x - self.entity.x,
                dest_y - self.entity.y,
            ).perform()

        return WaitAction(self.entity).perform()
