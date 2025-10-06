from __future__ import annotations
from typing import Tuple, List, Iterator, Dict, TYPE_CHECKING, Optional
from game_map import GameMap
import tile_types
import tcod
import copy
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
    0: [
        # TODO change spawn rate of ring back to reasonable percentage
        (entity_factory.wierd_ring, 1),
        (entity_factory.ossuary_loop, 1),
        (entity_factory.veinbinder, 1),
        (entity_factory.weeping_knuckle, 1),
        (entity_factory.phage_circlet, 1),
        (entity_factory.stitchband, 1),
        (entity_factory.maws_embrace, 1),
        (entity_factory.carrion_loop, 1),
        (entity_factory.throbbing_halo, 1),
        (entity_factory.tumors_promise, 1),
        (entity_factory.knotted_viscera_band, 1),
        (entity_factory.health_potion, 35),
        (entity_factory.mana_potion, 35),
        (entity_factory.large_health_potion, 5),
    ],
    2: [(entity_factory.confusion_scroll, 10)],
    4: [(entity_factory.lightning_scroll, 25), (entity_factory.sword, 5)],
    6: [(entity_factory.fireball_scroll, 25), (entity_factory.chain_mail, 15)],
}

enemy_chances: Dict[int, List[Tuple[Entity, int]]] = {
    0: [
        (entity_factory.orc, 10),
        (entity_factory.rat, 60),
        (entity_factory.goblin, 60),
    ],
    2: [(entity_factory.zombie, 1)],
    4: [(entity_factory.flesh_golem, 1), (entity_factory.vendor, 10)],
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


def generate_shop_items(entity: Entity, floor_number: int):
    if hasattr(entity, "inventory"):
        if entity.inventory.capacity > 0:
            items: List[Entity] = get_entities_at_random(item_chances, 5, floor_number)
            for item in items:
                l_hp = copy.deepcopy(item)

                l_hp.parent = entity.inventory
                entity.inventory.items.append(l_hp)


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
    boss: Optional[bool] = False,
    current_room: Optional[int] = 0,
) -> None:
    # choose random number of monsters and items
    monsters = []
    if not current_room == 0:
        number_of_monsters = random.randint(
            0, get_max_value_for_floor(max_monsters_by_floor, floor_number)
        )
        monsters: List[Entity] = get_entities_at_random(
            enemy_chances, number_of_monsters, floor_number
        )
    number_of_items = random.randint(
        0, get_max_value_for_floor(max_items_by_floor, floor_number)
    )
    items: List[Entity] = get_entities_at_random(
        item_chances, number_of_items, floor_number
    )
    for entity in monsters + items:
        x = random.randint(room.x1 + 1, room.x2 - 1)
        y = random.randint(room.y1 + 1, room.y2 - 1)
        if not any(entity.x == x and entity.y == y for entity in dungeon.entities):
            if "Mana" in entity.name and not dungeon.engine.player.is_mage:
                entity_factory.health_potion.spawn(dungeon, x, y)
                continue
            if "Organ" in entity.name and dungeon.vendor_spawned:
                entity_factory.orc.spawn(dungeon, x, y)
                continue
            elif "Organ" in entity.name:
                generate_shop_items(entity=entity, floor_number=floor_number)
                dungeon.vendor_spawned = True
            entity.spawn(dungeon, x, y)
    if floor_number == 5 and boss:
        entity_factory.lvl5_boss.spawn(
            dungeon,
            random.randint(room.x1 + 1, room.x2 - 1),
            random.randint(room.y1 + 1, room.y2 - 1),
        )


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
    is_last_room = False
    # iterate from 0 to max_rooms
    room_check = 0
    boss = False
    boss_count = 0
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
            room_check += 1
            continue
            # set tiles of room innter as floor
        dungeon.tiles[new_room.inner] = tile_types.randFloor()
        # this checks for first room if so player is placed in it
        if len(rooms) == 0:
            player.place(*new_room.center, dungeon)
            if engine.game_world.current_floor == 1:
                entity_factory.gorebound.spawn(dungeon, player.x - 2, player.y - 2)
                entity_factory.helixbound.spawn(dungeon, player.x + 2, player.y - 2)
            # this ensures that the first room is safe
        else:
            # now tunnels are built
            # with negative index to get previos room
            for x, y in tunnel_between(rooms[-1].center, new_room.center):
                dungeon.tiles[x, y] = tile_types.randFloor()
            center_of_last_room = new_room.center
        if len(rooms) >= 6 and not boss and boss_count == 0:
            boss_count = 1
            boss = True
        elif boss_count > 0:
            boss = False
        place_entities(
            new_room, dungeon, engine.game_world.current_floor, boss, len(rooms)
        )
        dungeon.tiles[center_of_last_room] = tile_types.stairs_up
        dungeon.upstairs_location = center_of_last_room
        # room is build sucessfully and appended
        rooms.append(new_room)
    return dungeon
