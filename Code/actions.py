from __future__ import annotations

from typing import Optional, Tuple, TYPE_CHECKING
import color
import exceptions
import random
from components.settings import GENERAL_CHEATS, PlayerClass

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
                signal = getattr(item, "on_pickup", None)
                if signal:
                    item.on_pickup = None
                    self.engine.game_map.fire(signal)
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
        if getattr(target, "invulnerable", False):
            raise exceptions.Impossible(f"{target.name} cannot be harmed.")
        for i in range(self.entity.fighter.attack_count):
            dmg_chance = random.randint(0, 100)
            if dmg_chance >= target.fighter.damage_reduction:
                # if self.dx == 2 or self.dx == -2 or self.dy == 2 or self.dy == -2:
                # crit damage on movement was OP. so changed
                # damage = self.entity.fighter.power * 2
                # damage = self.entity.fighter.power
                # else:
                damage = self.entity.fighter.power
                self.typal_damage()
            else:
                doged = True

            attack_desc = f"{self.entity.name.capitalize()} attacks {target.name}"
            # if self.dx == 2 or self.dx == -2 or self.dy == 2 or self.dy == -2:
            # attack_desc += " critically"
            if self.engine is self.engine.player:
                attack_color = color.player_atk
            else:
                attack_color = color.enemy_atk
            if damage > 0 and not doged:
                self.engine.message_log.add_message(
                    f"{attack_desc} for {damage} HP.", attack_color
                )
                if target == self.engine.player and GENERAL_CHEATS["god_mode"]:
                    pass
                else:
                    target.fighter.hp -= damage
            elif doged:
                self.engine.message_log.add_message(f"{attack_desc}, doged")
            else:
                self.engine.message_log.add_message(
                    f"{attack_desc} but does no damage.", attack_color
                )

    def typal_damage(self) -> None:
        # this function is supposed to represent damages to the class
        # specific functions ie. fighter takes mass damage
        if self.engine.player.player_class == PlayerClass.FIGHTER:
            damage_to_mass_probability = random.randint(0, 100)
            if damage_to_mass_probability <= (
                10 - self.engine.player.fighter.mass_level
            ):
                mass_damage = random.randint(1, 2)
                self.engine.message_log.add_message(
                    f"You're mass is damaged by {mass_damage}"
                )
                self.engine.player.fighter.mass -= mass_damage
                if self.engine.player.fighter.mass < 0:
                    self.engine.player.fighter.mass = 0


class MovementAction(ActionWithDirection):
    def perform(self):
        dest_x, dest_y = self.dest_xy

        # checks if movement would place player out of bounds
        if not self.engine.game_map.in_bounds(dest_x, dest_y):
            raise exceptions.Impossible("The way is blocked!")
        # checks if tile is walkable
        if not GENERAL_CHEATS["noclip"]:
            if not self.engine.game_map.tiles["walkable"][dest_x, dest_y]:
                raise exceptions.Impossible("Path inaccessible!")
            if self.engine.game_map.get_blocking_entity_at_location(dest_x, dest_y):
                raise exceptions.Impossible("The path is blocked!")
        # if above are correct movement is triggered
        self.entity.move(self.dx, self.dy)
        if self.entity is self.engine.player:
            from events import on_step

            previous = (dest_x - self.dx, dest_y - self.dy)
            on_step(self.engine.game_map, (dest_x, dest_y), previous)


class TileBumpAction(ActionWithDirection):
    """Base for level editor tiles that react when the player walks into them.
    Register subclasses in TILE_BUMPS under the name a TileDef uses as on_bump."""

    @staticmethod
    def wants(info: dict) -> bool:
        """Should bumping this tile run the action instead of moving/attacking?"""
        return True

    @property
    def info(self) -> dict:
        return self.engine.game_map.tile_state[self.dest_xy]


class PullLeverAction(TileBumpAction):
    def perform(self) -> None:
        from events import conditions_met

        game_map = self.engine.game_map
        info = self.info
        if not conditions_met(self.engine, info["props"]):
            raise exceptions.Impossible("The lever won't budge.")
        game_map.set_tile_state(self.dest_xy, "on" if info["state"] == "off" else "off")

        if game_map.fire(info["props"].get("link_id", "")):
            self.engine.message_log.add_message(
                "You pull the lever. Something grinds in the walls."
            )
        else:
            self.engine.message_log.add_message(
                "You pull the lever. Nothing happens.", color.impossible
            )


class UnlockDoorAction(TileBumpAction):
    @staticmethod
    def wants(info: dict) -> bool:
        return bool(info["props"].get("key_id")) and info["state"] != "open"

    def perform(self) -> None:
        info = self.info
        key = find_key(self.entity, info["props"]["key_id"])
        if key is None:
            if info["state"] == "hidden":
                # don't give the secret away
                raise exceptions.Impossible("Path inaccessible!")
            raise exceptions.Impossible("The door is locked.")

        self.engine.game_map.set_tile_state(self.dest_xy, "open")
        use_key(self.engine, self.entity, key, info["props"], "door")


def find_key(actor, quest_id: str):
    """The quest item in the actor's inventory that matches quest_id, or None."""
    return next(
        (i for i in actor.inventory.items if getattr(i, "quest_id", None) == quest_id),
        None,
    )


def use_key(engine, actor, key, props: dict, what: str) -> None:
    from tiles import is_yes

    if is_yes(props.get("consume_key")):
        actor.inventory.items.remove(key)
        engine.message_log.add_message(f"The {key.name} stays in the lock.")
    else:
        engine.message_log.add_message(f"You unlock the {what} with the {key.name}.")


class OpenChestAction(TileBumpAction):
    """Rolls the chest's loot table and drops the items around it."""

    @staticmethod
    def wants(info: dict) -> bool:
        return info["state"] == "closed"

    def perform(self) -> None:
        import entity_factory
        from components.loot import roll
        from entity import Item
        from events import conditions_met

        info = self.info
        props = info["props"]
        if not conditions_met(self.engine, props):
            raise exceptions.Impossible("The chest won't open.")
        if props.get("key_id"):
            key = find_key(self.entity, props["key_id"])
            if key is None:
                raise exceptions.Impossible("The chest is locked.")
            use_key(self.engine, self.entity, key, props, "chest")

        game_map = self.engine.game_map
        game_map.set_tile_state(self.dest_xy, "open")

        loot = roll(self.engine, props.get("loot_table", ""))
        guaranteed = getattr(entity_factory, props.get("guaranteed", ""), None)
        if isinstance(guaranteed, Item):
            loot.insert(0, guaranteed)

        spots = self.drop_spots()
        names = []
        for i, prototype in enumerate(loot):
            item = prototype.spawn(game_map, *spots[i % len(spots)])
            names.append(item.name)
        if names:
            counts = {}  # keeps the order items came out in
            for name in names:
                counts[name] = counts.get(name, 0) + 1
            listed = ", ".join(
                f"{name} x{count}" if count > 1 else name for name, count in counts.items()
            )
            self.engine.message_log.add_message(
                f"You open the chest: {listed}.", color.menu_title
            )
        else:
            self.engine.message_log.add_message("You open the chest. It is empty.")

        game_map.fire(props.get("link_id", ""))

    def drop_spots(self) -> list:
        """Walkable cells around the chest, closest to the player first."""
        game_map = self.engine.game_map
        cx, cy = self.dest_xy
        spots = [
            (cx + dx, cy + dy)
            for dx in (-1, 0, 1)
            for dy in (-1, 0, 1)
            if (dx or dy)
            and game_map.in_bounds(cx + dx, cy + dy)
            and game_map.tiles["walkable"][cx + dx, cy + dy]
        ]
        spots.sort(key=lambda spot: self.entity.distance(*spot))
        return spots or [(self.entity.x, self.entity.y)]


# TileDef.on_bump name -> action, see tiles.py
TILE_BUMPS = {
    "lever": PullLeverAction,
    "door": UnlockDoorAction,
    "chest": OpenChestAction,
}


class BumpAction(ActionWithDirection):
    def perform(self) -> None:
        game_map = self.engine.game_map
        info = getattr(game_map, "tile_state", {}).get(self.dest_xy)
        if info is not None and self.entity is self.engine.player:
            from tiles import TILE_BY_ID

            bump = TILE_BUMPS.get(TILE_BY_ID[info["tile"]].on_bump)
            if bump is not None and bump.wants(info):
                return bump(self.entity, self.dx, self.dy).perform()
        if self.target_actor:
            # if entity is a vendor meele action is disabled
            if not self.target_actor.name == "Organ trader":
                if self.entity.player_class == PlayerClass.ROUGE:
                    MovementCheck(dx=self.dx, dy=self.dy, entity=self.entity)
                return MeleeAction(self.entity, self.dx, self.dy).perform()
        else:
            if "2" in str(self.dx) or "2" in str(self.dy):
                if not GENERAL_CHEATS["inf_stamina"]:
                    self.entity.fighter.stamina -= 2
            return MovementAction(self.entity, self.dx, self.dy).perform()


# Function to check whether the stamina action of the Rouge is permitted
def MovementCheck(dx, dy, entity):
    if "2" in str(dx) or "2" in str(dy) and entity.fighter.stamina >= 10:
        if not GENERAL_CHEATS["inf_stamina"]:
            entity.fighter.stamina -= 10
    else:
        return dx / 2, dy / 2


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


class CastSpell(Action):
    def perform(self, spell=None) -> None:
        pass
