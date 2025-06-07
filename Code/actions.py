from __future__ import annotations

from typing import Optional, Tuple, TYPE_CHECKING, Dict
import color
import exceptions
import random
import components.effects as ef

if TYPE_CHECKING:
    from engine import Engine
    from entity import Actor, Entity, Item

    # import components.effects


class Action:
    def __init__(self, entity: Actor) -> None:
        super().__init__()
        self.entity = entity

    @property
    def engine(self) -> Engine:
        return self.entity.gamemap.engine

    def perform(self) -> None:
        raise NotImplementedError()


class EquipAction(Action):
    def __init__(self, entity, item: Item):
        super().__init__(entity)
        self.item = item

    def perform(self):
        self.entity.equipment.toggle_equip(self.item)


class WaitAction(Action):
    def perform(self):
        pass


class TakeStairsAction(Action):
    def perform(self):
        if (self.entity.x, self.entity.y) == self.engine.game_map.upstairs_location:
            self.engine.game_world.generate_floor()
            self.engine.message_log.add_message(
                "You go up the fleshy stairs", color.ascend
            )
        else:
            raise exceptions.Impossible("No stairs here")


class PickupAction(Action):
    def __init__(self, entity: Actor):
        super().__init__(entity)

    def perform(self) -> None:
        actor_location_x = self.entity.x
        actor_location_y = self.entity.y
        inventory = self.entity.inventory

        for item in self.engine.game_map.items:
            if actor_location_x == item.x and actor_location_y == item.y:
                if len(inventory.items) >= inventory.capacity:
                    raise exceptions.Impossible("Inventoy full!")

                self.engine.game_map.entities.remove(item)
                item.parent = self.entity.inventory
                inventory.items.append(item)

                self.engine.message_log.add_message(f"You pick up {item.name}!")
                return
        raise exceptions.Impossible("You grab the floor?")


class ItemAction(Action):
    def __init__(
        self, entity: Actor, item: Item, target_xy: Optional[Tuple[int, int]] = None
    ):
        super().__init__(entity)
        self.item = item
        if not target_xy:
            target_xy = entity.x, entity.y
        self.target_xy = target_xy

    @property
    def target_actor(self) -> Optional[Actor]:
        return self.engine.game_map.get_actor_at_location(*self.target_xy)

    def perform(self) -> None:
        if self.item.consumable:
            self.item.consumable.activate(self)


class DropItem(ItemAction):
    def perform(self):
        if self.entity.equipment.item_is_equipped(self.item):
            self.entity.equipment.toggle_equip(self.item)

        self.entity.inventory.drop(self.item)


class ActionWithDirection(Action):
    def __init__(self, entity: Actor, dx: int, dy: int):
        super().__init__(entity)
        self.dx = dx
        self.dy = dy

    @property
    def dest_xy(self) -> Tuple[int, int]:
        """Returns this actions destination."""
        return self.entity.x + self.dx, self.entity.y + self.dy

    @property
    def blocking_entity(self) -> Optional[Entity]:
        """Return the blocking entity at this actions destination.."""
        return self.engine.game_map.get_blocking_entity_at_location(*self.dest_xy)

    @property
    def target_actor(self) -> Optional[Actor]:
        return self.engine.game_map.get_actor_at_location(*self.dest_xy)

    def perform(self) -> None:
        raise NotImplementedError()


class MeleeAction(ActionWithDirection):
    def perform(self) -> None:
        target = self.target_actor
        doged = False
        damage = 0
        if not target:
            raise exceptions.Impossible("Nothing to attack.")
        dmg_chance = random.randint(0, 100)
        if dmg_chance >= target.fighter.damage_reduction:
            damage = self.entity.fighter.power
        else:
            doged = True

        attack_desc = f"{self.entity.name.capitalize()} attacks {target.name}"
        if self.engine is self.engine.player:
            attack_color = color.player_atk
        else:
            attack_color = color.enemy_atk
        if damage > 0 and not doged:
            self.engine.message_log.add_message(
                f"{attack_desc} for {damage} HP.", attack_color
            )
            target.fighter.hp -= damage
        elif doged:
            self.engine.message_log.add_message(f"{attack_desc}, doged")
        else:
            self.engine.message_log.add_message(
                f"{attack_desc} but does no damage.", attack_color
            )


class MovementAction(ActionWithDirection):

    def perform(self):
        dest_x, dest_y = self.dest_xy

        # checks if movement would place player out of bounds
        if not self.engine.game_map.in_bounds(dest_x, dest_y):
            raise exceptions.Impossible("The way is blocked!")
        # checks if tile is walkable
        if not self.engine.game_map.tiles["walkable"][dest_x, dest_y]:
            raise exceptions.Impossible("Path inaccessible!")
        if self.engine.game_map.get_blocking_entity_at_location(dest_x, dest_y):
            raise exceptions.Impossible("The path is blocked!")
        # if above are correct movement is triggered
        self.entity.move(self.dx, self.dy)


class BumpAction(ActionWithDirection):
    def perform(self) -> None:
        if self.target_actor:
            # if entity is a vendor meele action is disabled
            if not self.target_actor.name == "Organ trader":
                return MeleeAction(self.entity, self.dx, self.dy).perform()
        else:
            return MovementAction(self.entity, self.dx, self.dy).perform()


class ConsumeCorpseAction(Action):
    def perform(self):
        for corpse in self.engine.game_map.entities:
            if (
                corpse.x == self.entity.x
                and corpse.y == self.entity.y
                and corpse != self.entity
            ):
                corpse.effect.activate(self.engine, corpse)
                return
        raise exceptions.Impossible("No corpse here")
