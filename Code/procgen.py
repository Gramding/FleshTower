from __future__ import annotations
from typing import Tuple, List, Iterator, TYPE_CHECKING
from game_map import GameMap
import tile_types
import tcod
import entity_factory
import random

if TYPE_CHECKING:
    from engine import Engine


class RectangularRoom:
    def __init__(self, x: int, y: int, width: int, height: int):
        self.x1 = x
        self.y1 = y
        self.x2 = x + width
        self.y2 = y + height

    @property
    def center(self) -> Tuple[int, int]:
        center_x = int((self.x1 + self.x2) / 2)
        center_y = int((self.y1 + self.y2) / 2)

        return center_x, center_y

    @property
    def inner(self) -> tuple[slice, slice]:
        return slice(self.x1 + 1, self.x2), slice(self.y1 + 1, self.y2)

    def intersects(self, other: RectangularRoom) -> bool:
        # this checks if 2 rooms would intersect
        # it does this by comparing coordinates
        # if intersectrion is detected return true
        # else return false
        return (
            self.x1 <= other.x2
            and self.x2 >= other.x1
            and self.y1 <= other.y2
            and self.y2 >= other.y1
        )


def place_entities(
    room: RectangularRoom,
    dungeon: GameMap,
    maximum_monsters: int,
    maximum_items: int,
) -> None:
    # choose random number of monsters
    number_of_monsters = random.randint(0, maximum_monsters)
    number_of_items = random.randint(0, maximum_items)
    # iterate for each monster to be palced
    for i in range(number_of_monsters):
        # get random positions of monster
        x = random.randint(room.x1 + 1, room.x2 - 1)
        y = random.randint(room.y1 + 1, room.y2 - 1)

        if not any(entity.x == x and entity.y == y for entity in dungeon.entities):
            if random.random() < 0.8:
                entity_factory.orc.spawn(dungeon, x, y)
            else:
                entity_factory.troll.spawn(dungeon, x, y)

    for i in range(number_of_items):
        x = random.randint(room.x1 + 1, room.x2 - 1)
        y = random.randint(room.y1 + 1, room.y2 - 1)

        if not any(entity.x == x and entity.y == y for entity in dungeon.entities):
            entity_factory.health_potion.spawn(dungeon, x, y)


def tunnel_between(
    start: Tuple[int, int], end: Tuple[int, int]
) -> Iterator[Tuple[int, int]]:
    x1, y1 = start
    x2, y2 = end
    if random.random() < 0.5:
        corner_x, corner_y = x2, y1
    else:
        corner_x, corner_y = x1, y2

    # yield allows the function to keep local state
    # this means that the calculations and such that were made, still hold true to the current state
    # therfore the tunnel can be build randomly and be connected to previous state
    for x, y in tcod.los.bresenham((x1, y1), (corner_x, corner_y)).tolist():
        yield x, y
    for x, y in tcod.los.bresenham((corner_x, corner_y), (x2, y2)).tolist():
        yield x, y


def generate_dungeon(
    max_rooms: int,  # max number of rooms in dungeon
    room_min_size: int,  # minimum size of a room in dungeon
    room_max_size: int,  # max size of a room in dungeon
    map_width: int,  # width of map
    map_height: int,  # height of map
    max_monsters_per_room: int,
    max_items_per_room,
    engine: Engine,
) -> GameMap:
    # create new dungeon
    player = engine.player
    dungeon = GameMap(engine, map_width, map_height, entities=[player])
    # this is a runnning list of all the rooms generated
    rooms: List[RectangularRoom] = []
    # iterate from 0 to max_rooms
    for r in range(max_rooms):
        # randomly generate the size of the room
        room_width = random.randint(room_min_size, room_max_size)
        room_height = random.randint(room_min_size, room_max_size)

        # randomly get the position of the room
        x = random.randint(0, dungeon.width - room_width - 1)
        y = random.randint(0, dungeon.height - room_height - 1)
        # creates the rect room
        new_room = RectangularRoom(x, y, room_width, room_height)
        # check if current room intersects with other room already generated
        if any(new_room.intersects(other_room) for other_room in rooms):
            # continue (dont use this one and start anew)
            continue
        # set tiles of room innter as floor
        dungeon.tiles[new_room.inner] = tile_types.floor
        # this checks for first room if so player is placed in it
        if len(rooms) == 0:
            player.place(*new_room.center, dungeon)
        else:
            # now tunnels are built
            # with negative index to get previos room
            for x, y in tunnel_between(rooms[-1].center, new_room.center):
                dungeon.tiles[x, y] = tile_types.floor

        place_entities(new_room, dungeon, max_monsters_per_room, max_items_per_room)
        # room is build sucessfully and appended
        rooms.append(new_room)
    return dungeon
