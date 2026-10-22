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
        from components import stats

        fighter = self.entity.fighter
        if stats.STAMINA_REGEN_ON_WAIT and self.entity is self.engine.player:
            fighter.stamina = min(fighter.max_stamina, fighter.stamina + fighter.stamina_regen)


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
        if not target:
            raise exceptions.Impossible("Nothing to attack.")
        if getattr(target, "invulnerable", False):
            raise exceptions.Impossible(f"{target.name} cannot be harmed.")

        from components import stats

        diagonal = self.dx != 0 and self.dy != 0
        if diagonal and self.entity is not self.engine.player and not stats.ENEMY_DIAGONAL_ATTACKS:
            raise exceptions.Impossible("Enemies can't attack diagonally.")  # e.g. confused

        player = self.engine.player
        attack_color = color.player_atk if self.entity is player else color.enemy_atk
        attack_desc = f"{self.entity.name.capitalize()} attacks {target.name}"
        power = self.entity.fighter.power
        if abs(self.dx) == 2 or abs(self.dy) == 2:  # Whisperbound lunge
            power *= stats.LUNGE_DAMAGE
            attack_desc = f"{self.entity.name.capitalize()} lunges at {target.name}"
        for _ in range(self.entity.fighter.attack_count):
            if not target.is_alive:
                break
            if random.randint(1, 100) <= target.fighter.dodge:
                self.engine.message_log.add_message(f"{attack_desc}, dodged")
                continue
            if target is player and GENERAL_CHEATS["god_mode"]:
                continue
            damage = target.fighter.take_damage(power)
            if damage:
                text = f"{attack_desc} for {damage} HP."
            else:
                text = f"{attack_desc} but the blow glances off."
            self.engine.message_log.add_message(text, attack_color)
            if target is player:
                self.typal_damage()

    def typal_damage(self) -> None:
        """Class specific damage when the player is hit: the Gorebound may
        lose mass."""
        fighter = self.engine.player.fighter
        if self.engine.player.player_class != PlayerClass.FIGHTER:
            return
        if random.randint(1, 100) <= fighter.mass_loss_chance:
            mass_damage = min(fighter.mass, random.randint(1, 2))
            if mass_damage:
                fighter.mass -= mass_damage
                self.engine.message_log.add_message(f"Your mass is damaged by {mass_damage}")


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
        import rules

        game_map = self.engine.game_map
        info = self.info
        if not rules.props_met(self.engine, info["props"]):
            raise exceptions.Impossible("The lever won't budge.")
        game_map.set_tile_state(self.dest_xy, "on" if info["state"] == "off" else "off")

        if game_map.fire(info["props"].get("signal", "")):
            self.engine.message_log.add_message(
                "You pull the lever. Something grinds in the walls."
            )
        else:
            self.engine.message_log.add_message(
                "You pull the lever. Nothing happens.", color.impossible
            )


class UnlockDoorAction(TileBumpAction):
    """A closed door with conditions (rules.py) opens for good when they hold:
    a key is "requires", a flag can lock it too."""

    @staticmethod
    def wants(info: dict) -> bool:
        import rules

        return bool(rules.conditions_from_props(info["props"])) and info["state"] != "open"

    def perform(self) -> None:
        import rules

        info = self.info
        if info["state"] == "hidden" and not rules.props_met(self.engine, info["props"]):
            raise exceptions.Impossible("Path inaccessible!")  # don't give the secret away
        check_lock(self.engine, info["props"], "door")
        self.engine.game_map.set_tile_state(self.dest_xy, "open")


def check_lock(engine, props: dict, what: str) -> None:
    """Doors and chests: raises Impossible when their conditions fail, else
    uses the required item (taken when consume is yes)."""
    import rules
    from tiles import is_yes

    failed = rules.failed_condition(engine, rules.conditions_from_props(props))
    if failed is not None:
        reason = "is locked" if failed[0] == "requires" else "won't open"
        raise exceptions.Impossible(f"The {what} {reason}.")
    item = rules.carried_quest_item(engine.player, props.get("requires", ""))
    if item is None:
        return
    if is_yes(props.get("consume")):
        engine.player.inventory.items.remove(item)
        engine.message_log.add_message(f"The {item.name} stays in the lock.")
    else:
        engine.message_log.add_message(f"You unlock the {what} with the {item.name}.")


class OpenChestAction(TileBumpAction):
    """Rolls the chest's loot table and drops the items around it."""

    @staticmethod
    def wants(info: dict) -> bool:
        return info["state"] == "closed"

    def perform(self) -> None:
        import rules
        from components.loot import roll

        info = self.info
        props = info["props"]
        check_lock(self.engine, props, "chest")

        game_map = self.engine.game_map
        game_map.set_tile_state(self.dest_xy, "open")

        loot = roll(self.engine, props.get("loot_table", ""))
        if props.get("gives"):  # always in this chest: a data item or a quest item
            loot.insert(0, rules.make_item(props["gives"]))

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

        game_map.fire(props.get("signal", ""))

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
        sprint = abs(self.dx) == 2 or abs(self.dy) == 2
        if self.target_actor:
            # if entity is a vendor meele action is disabled
            if not self.target_actor.name == "Organ trader":
                if sprint:
                    spend_stamina(self.entity, self.entity.fighter.lunge_cost, "lunge")
                return MeleeAction(self.entity, self.dx, self.dy).perform()
        else:
            if sprint:
                spend_stamina(self.entity, self.entity.fighter.sprint_cost, "sprint")
            return MovementAction(self.entity, self.dx, self.dy).perform()


def spend_stamina(entity, cost: int, what: str) -> None:
    """Whisperbound sprinting: 2 tiles at once costs stamina."""
    if GENERAL_CHEATS["inf_stamina"]:
        return
    if entity.fighter.stamina < cost:
        raise exceptions.Impossible(f"You are too exhausted to {what}.")
    entity.fighter.stamina -= cost


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
