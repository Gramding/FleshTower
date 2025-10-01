from __future__ import annotations

import copy
import math
from typing import Optional, Tuple, Type, TypeVar, TYPE_CHECKING, Union, List, Dict

from render_order import RenderOrder

if TYPE_CHECKING:
    from components.ai import BaseAI
    from components.consumable import Consumable
    from components.equippable import Equippable
    from components.equipment import Equipment
    from components.fighter import Fighter
    from components.inventory import Inventory
    from components.level import Level
    from game_map import GameMap
    from components.spells import SpellBook
    from components.effects import LogBook, Effect

T = TypeVar("T", bound="Entity")


class Entity:
    # this is a generic class to represent every entity in game
    # the player enemies items etc.
    parent: Union[GameMap, Inventory]

    def __init__(
        self,
        parent: Optional[GameMap] = None,
        x: int = 0,
        y: int = 0,
        char: str = "?",
        color: Tuple[int, int, int] = (255, 255, 255),
        name: str = "<unnamed>",
        blocks_movement: bool = False,
        render_order: RenderOrder = RenderOrder.CORPSE,
    ):
        # set object variables
        self.x = x  # cords of entity
        self.y = y
        self.char = (
            char  # this is the character that represents the entity (player = @)
        )
        self.color = color  # color of entity
        self.name = name  # name of entity
        self.blocks_movement = blocks_movement  # blocks or does not block movement
        self.render_order = render_order
        if parent:
            self.parent = parent
            parent.entities.add(self)

    @property
    def gamemap(self) -> GameMap:
        return self.parent.gamemap

    def spawn(self: T, gamemap: GameMap, x: int, y: int) -> T:
        clone = copy.deepcopy(self)
        clone.x = x
        clone.y = y
        clone.parent = gamemap
        gamemap.entities.add(clone)
        return clone

    def place(self, x: int, y: int, gamemap: Optional[GameMap] = None) -> None:
        self.x = x
        self.y = y
        if gamemap:
            if hasattr(self, "parent"):
                if self.parent is self.gamemap:
                    self.gamemap.entities.remove(self)
            self.parent = gamemap
            gamemap.entities.add(self)

    def distance(self, x: int, y: int) -> float:
        return math.sqrt((x - self.x) ** 2 + (y - self.y) ** 2)

    def move(self, dx: int, dy: int) -> None:
        self.x += dx
        self.y += dy


class Actor(Entity):

    def __init__(
        self,
        *,
        x: int = 0,
        y: int = 0,
        char: str = "?",
        color: Tuple[int, int, int] = (255, 255, 255),
        name: str = "<Unnamed>",
        ai_cls: Type[BaseAI],
        fighter: Fighter,
        equipment: Equipment,
        inventory: Inventory,
        spellbook: SpellBook,
        logbook: LogBook,
        effect: Effect,
        level: Level,
    ):
        super().__init__(
            x=x,
            y=y,
            char=char,
            color=color,
            name=name,
            blocks_movement=True,
            render_order=RenderOrder.ACTOR,
        )
        self.ai: Optional[BaseAI] = ai_cls(self)

        self.fighter = fighter
        self.fighter.parent = self
        self.inventory = inventory
        self.inventory.parent = self
        self.level = level
        self.level.parent = self
        self.equipment: Equipment = equipment
        self.equipment.parent = self
        self.is_rouge = True
        self.is_mage = False
        self.is_fighter = False
        self.spellbook: SpellBook = spellbook
        self.effect = effect
        self.logbook: LogBook = logbook
        self.currency = 0


    @property
    def is_alive(self) -> bool:
        return bool(self.ai)
    @property
    def class_name(self) -> str:
        if self.is_fighter:
            return f"Gorebound {self.fighter.mass_level}"
        elif self.is_mage:
            return  "Helixbound"
        elif self.is_rouge:
            return  "Whisperbound"


class Item(Entity):
    def __init__(
        self,
        *,
        x: int = 0,
        y: int = 0,
        char: str = "?",
        color: Tuple[int, int, int] = (255, 255, 255),
        name: str = "<Unnamed>",
        consumable: Optional[Consumable] = None,
        equippable: Optional[Equippable] = None,
        effect: Effect,
        price: int,
    ):
        super().__init__(
            x=x,
            y=y,
            char=char,
            color=color,
            name=name,
            blocks_movement=False,
            render_order=RenderOrder.ITEM,
        )
        self.price = price
        self.effect = effect
        self.consumable = consumable
        if self.consumable:
            self.consumable.parent = self

        self.equippable = equippable

        if self.equippable:
            self.equippable.parent = self
