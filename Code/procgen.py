from __future__ import annotations
from typing import Tuple, List, Iterator, Dict, TYPE_CHECKING
from game_map import GameMap
import tile_types
import tcod
import entity_factory
import random

if TYPE_CHECKING:
    from engine import Engine
    from entity import Entity

max_items_by_floor = [
    (1, 1),
    (4, 2),
]

max_monsters_by_floor = [
    (1, 2),
    (4, 3),
    (6, 5),
]

item_chances: Dict[int, List[Tuple[Entity, int]]] = {
    0: [(entity_factory.health_potion, 35)],
    2: [(entity_factory.confusion_scroll, 10)],
    4: [(entity_factory.lightning_scroll, 25), (entity_factory.sword, 5)],
    6: [(entity_factory.fireball_scroll, 25), (entity_factory.chain_mail, 15)],
}

enemy_chances: Dict[int, List[Tuple[Entity, int]]] = {
    0: [(entity_factory.orc, 80)],
    3: [(entity_factory.troll, 15)],
    5: [(entity_factory.troll, 30)],
    7: [(entity_factory.troll, 60)],
}


def get_max_value_for_floor(
    max_value_by_floor: List[Tuple[int, int]], floor: int
) -> int:
    current_value = 0

    for floor_minimum, value in max_value_by_floor:
        if floor_minimum > floor:
            break
        else:
            current_value = value

        return current_value


def get_entities_at_random(
    weighted_chances_by_floor: Dict[int, List[Tuple[Entity, int]]],
    number_of_entities: int,
    floor: int,
) -> List[Entity]:
    entity_weighted_chances = {}
    for key, values in weighted_chances_by_floor.items():
        if key > floor:
            break
        else:
            for value in values:
                entity = value[0]
                weighted_chance = value[1]
                entity_weighted_chances[entity] = weighted_chance

    entities = list(entity_weighted_chances.keys())
    entity_weighted_chance_values = list(entity_weighted_chances.values())
    chosen_entities = random.choices(
        entities, weights=entity_weighted_chance_values, k=number_of_entities
    )

    return chosen_entities


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
    floor_number: int,
) -> None:
    # choose random number of monsters and items
    number_of_monsters = random.randint(
        0, get_max_value_for_floor(max_monsters_by_floor, floor_number)
    )
    number_of_items = random.randint(
        0, get_max_value_for_floor(max_items_by_floor, floor_number)
    )

    monsters: List[Entity] = get_entities_at_random(
        enemy_chances, number_of_monsters, floor_number
    )
    items: List[Entity] = get_entities_at_random(
        item_chances, number_of_items, floor_number
    )
    for entity in monsters + items:
        x = random.randint(room.x1 + 1, room.x2 - 1)
        y = random.randint(room.y1 + 1, room.y2 - 1)
        if not any(entity.x == x and entity.y == y for entity in dungeon.entities):
            entity.spawn(dungeon, x, y)


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
    engine: Engine,
) -> GameMap:
    # create new dungeon
    player = engine.player
    dungeon = GameMap(engine, map_width, map_height, entities=[player])
    # this is a runnning list of all the rooms generated
    rooms: List[RectangularRoom] = []
    center_of_last_room = (0, 0)
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
            center_of_last_room = new_room.center

        place_entities(new_room, dungeon, engine.game_world.current_floor)
        dungeon.tiles[center_of_last_room] = tile_types.stairs_up
        dungeon.upstairs_location = center_of_last_room
        # room is build sucessfully and appended
        rooms.append(new_room)
    return dungeon
