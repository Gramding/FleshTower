from __future__ import annotations

from typing import Iterable, Iterator, Optional, TYPE_CHECKING
import numpy as np  # type: ignore
from tcod.console import Console
import random

from entity import Actor, Item
import tile_types

if TYPE_CHECKING:
    from engine import Engine
    from entity import Entity


class GameMap:
    def __init__(
        self, engine: Engine, width: int, height: int, entities: Iterable[Entity] = ()
    ):
        self.engine = engine
        self.vendor_spawned = False
        self.width = width
        self.height = height
        self.entities = set(entities)
        self.tiles = np.full(
            (width, height), fill_value=tile_types.randWall(), order="F"
        )

        self.visible = np.full(
            (width, height), fill_value=False, order="F"
        )  # this returns tiles the player sees
        self.explored = np.full(
            (width, height), fill_value=False, order="F"
        )  # this is tiles the player has seen before

        self.upstairs_location = (int(0), int(0))

    @property
    def gamemap(self) -> GameMap:
        return self

    @property
    def actors(self) -> Iterator[Actor]:
        yield from (
            entity
            for entity in self.entities
            if isinstance(entity, Actor) and entity.is_alive
        )

    @property
    def items(self) -> Iterator[Item]:
        yield from (entity for entity in self.entities if isinstance(entity, Item))

    def get_blocking_entity_at_location(
        self, location_X: int, location_y: int
    ) -> Optional[Entity]:
        for entity in self.entities:
            if (
                entity.blocks_movement
                and entity.x == location_X
                and entity.y == location_y
            ):
                return entity
        return None

    def get_actor_at_location(self, x: int, y: int) -> Optional[Actor]:
        for actor in self.actors:
            if actor.x == x and actor.y == y:
                return actor
        return None

    def in_bounds(self, x: int, y: int) -> bool:
        # returns true if give x and y are within the maps boundaries
        return 0 <= x < self.width and 0 <= y < self.height

    def render(self, console: Console) -> None:
        # this renders the entire map
        o_x, o_y, e_x, e_y = self.get_viewport()
        s_x = slice(o_x, e_x + 1)
        s_y = slice(o_y, e_y + 1)
        viewport_tiles = self.tiles[s_x, s_y]  # [o_x:e_x+1,o_y:e_y + 1]
        viewport_visible = self.visible[s_x, s_y]
        viewport_explored = self.explored[s_x, s_y]

        console.rgb[
            0 : self.engine.game_world.viewport_width,
            0 : self.engine.game_world.viewport_height,
        ] = np.select(
            condlist=[viewport_visible, viewport_explored],
            choicelist=[viewport_tiles["light"], viewport_tiles["dark"]],
            default=tile_types.SHROUD,
        )
        entities_sorted_for_rendering = sorted(
            self.entities, key=lambda x: x.render_order.value
        )
        for entity in entities_sorted_for_rendering:
            if self.visible[entity.x, entity.y]:
                console.print(
                    x=entity.x - o_x,
                    y=entity.y - o_y,
                    text=entity.char,
                    fg=entity.color,
                )

    def get_viewport(self):
        x = self.engine.player.x
        y = self.engine.player.y
        width = self.engine.game_world.viewport_width
        height = self.engine.game_world.viewport_height
        half_width = int(width / 2)
        half_height = int(height / 2)
        origin_x = x - half_width
        origin_y = y - half_height
        # print(f'player: ({x}, {y}), modifier: {half_width}, {half_height}, origin: ({origin_x}, {origin_y})')
        if origin_x < 0:
            origin_x = 0
        if origin_y < 0:
            origin_y = 0

        end_x = origin_x + width
        end_y = origin_y + height
        # print(f'End: ({end_x},{end_y})')
        if end_x > self.width:
            x_diff = end_x - self.width
            origin_x -= x_diff
            end_x -= x_diff

        if end_y > self.height:
            y_diff = end_y - self.height
            origin_y -= y_diff
            end_y -= y_diff
        return (origin_x, origin_y, end_x - 1, end_y - 1)


class GameWorld:
    def __init__(
        self,
        engine: Engine,
        map_width: int,
        map_height: int,
        max_rooms: int,
        room_min_size: int,
        room_max_size: int,
        current_floor: int = -1,
        viewport_width: int = 0,
        viewport_height: int = 0,
    ):
        self.engine = engine

        self.viewport_width = viewport_width
        self.viewport_height = viewport_height

        self.map_width = map_width
        self.map_height = map_height

        self.max_rooms = max_rooms

        self.room_min_size = room_min_size
        self.room_max_size = room_max_size

        self.current_floor = current_floor

    def generate_floor(self) -> None:
        from procgen import generate_dungeon
        from procgen import generate_class_select
        from procgen import generate_shop_room
        from procgen import generate_boss_room

        self.current_floor += 1
        shop_chance = random.randint(0, 100)
        # self.randSizes()
        # Small description
        # Check if floor is 0 for character creation room
        # if shop is rolled and its not the first floor or a floor number divisibile by 5 a shop room gets spawned
        # if floor number is increment of 5 spawn a boss fight
        # if not any of the above gen a normal floor
        if self.current_floor == 0:
            self.engine.game_map = generate_class_select(
                map_width=self.map_width, map_height=self.map_height, engine=self.engine
            )
        elif (
            shop_chance <= 20
            and not self.current_floor == 1
            and not self.current_floor % 5 == 0
        ):
            self.engine.game_map = generate_shop_room(
                map_width=self.map_width,
                map_height=self.map_height,
                engine=self.engine,
                current_floor=self.current_floor,
            )
        elif self.current_floor % 5 == 0:
            self.engine.game_map = generate_boss_room(
                map_width=self.map_width,
                map_height=self.map_height,
                engine=self.engine,
                current_floor=self.current_floor,
            )
        else:
            self.engine.game_map = generate_dungeon(
                max_rooms=self.max_rooms,
                room_min_size=self.room_min_size,
                room_max_size=self.room_max_size,
                map_width=self.map_width,
                map_height=self.map_height,
                engine=self.engine,
            )

    def randSizes(self):
        # define ranges for floor numbers
        self.max_rooms += self.current_floor
        self.room_min_size = random.randint(
            self.room_min_size, self.room_min_size + self.current_floor
        )
        self.room_max_size = random.randint(
            self.room_max_size, self.room_max_size + self.current_floor
        )
