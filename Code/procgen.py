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
    (2, 2),
    (3, 2),
    (4, 3),
    (5, 3),
    (6, 4),
    (7, 4),
    (8, 5),
]

max_monsters_by_floor = [
    (1, 2),
    (2, 2),
    (3, 3),
    (4, 3),
    (5, 4),
    (6, 5),
    (7, 5),
    (8, 6),
]
#TODO Check why if one item is generated only this item gets chosen afterwards
#if sinewcleaver is generated only sinewcleaver is getting generated
#this is wrong and needs fixing
item_chances: Dict[int, List[Tuple[Entity, int]]] = {
    0: [
        # Common early loot
        (entity_factory.health_potion, 35),
        (entity_factory.mana_potion, 35),
        (entity_factory.large_health_potion, 5),

        # Rare early rings
        (entity_factory.wierd_ring, 1),
        (entity_factory.ossuary_loop, 1),
        (entity_factory.veinbinder, 1),

        # Early weapons (basic melee gear)
        (entity_factory.neural_razor, 5),
        (entity_factory.sinewcleaver, 5),
        (entity_factory.spine_talon, 4),

        # Early headgear
        (entity_factory.crimson_skullcap, 2),
        (entity_factory.boneplate_hood, 2),
        (entity_factory.sinewcap, 2),

        # Early eyes
        (entity_factory.blindeye_lenses, 2),
        (entity_factory.hemogaze_lens, 2),

        # Early necklace
        (entity_factory.throatlace, 1),
        (entity_factory.humeral_chain, 1),

        # Early cloak
        (entity_factory.shredded_shroud, 2),
        (entity_factory.skinfold_mantle, 2),

        # Early wrist
        (entity_factory.gristle_bracer, 2),
        (entity_factory.bone_cuffs, 2),

        # Early belt
        (entity_factory.guts_belt, 2),
        (entity_factory.rib_binder, 2),

        # Early legs
        (entity_factory.shredded_greaves, 2),
        (entity_factory.bone_spliced_trousers, 2),
    ],

    2: [
        # Utility scrolls and early upgrades
        (entity_factory.confusion_scroll, 10),
        (entity_factory.gristle_hook, 4),
        (entity_factory.viscera_blade, 3),

        # Slightly stronger gear starts appearing
        (entity_factory.ooze_crowned_cap, 1),
        (entity_factory.veinwoven_circlet, 1),
        (entity_factory.tumor_amulet, 1),
        (entity_factory.cystic_cape, 1),
        (entity_factory.throbbing_band, 1),
        (entity_factory.tendon_girdle, 1),
    ],

    4: [
        # Mid-tier loot and solid weapons
        (entity_factory.lightning_scroll, 25),
        (entity_factory.sword, 5),
        (entity_factory.phage_fang, 3),
        (entity_factory.knotted_mace, 3),

        # Mid-tier headgear
        (entity_factory.flayed_helm, 2),
        (entity_factory.pulsing_cranium, 2),

        # Mid-tier eyes
        (entity_factory.third_orb, 1),
        (entity_factory.eye_of_the_wyrm, 1),

        # Mid-tier necklace
        (entity_factory.sinew_choker, 1),
        (entity_factory.veinloop_necklace, 1),

        # Mid-tier cloak
        (entity_factory.vein_mantle, 2),
        (entity_factory.tendril_cloak, 1),

        # Mid-tier wrist
        (entity_factory.tumorous_wristguard, 1),
        (entity_factory.veinlace_wristband, 1),

        # Mid-tier belt
        (entity_factory.visceral_cinch, 1),
        (entity_factory.fleshbinder, 1),

        # Mid-tier legs
        (entity_factory.vein_wrapped_leggings, 2),
        (entity_factory.tendon_laced_pants, 1),
    ],

    5: [
        # Rare mid-high items start appearing
        (entity_factory.marrow_saw, 2),
        (entity_factory.bonegrinder_maul, 2),

        # High-tier headgear
        (entity_factory.tumor_crowned_helm, 1),
        (entity_factory.marrow_visage, 1),

        # High-tier eyes
        (entity_factory.corrupted_iris, 1),
        (entity_factory.pustular_eyeband, 1),

        # High-tier necklace
        (entity_factory.ossified_torque, 1),
        (entity_factory.rib_bound_medallion, 1),

        # High-tier cloak
        (entity_factory.marrow_veil, 1),
        (entity_factory.flesh_tattered_robe, 1),

        # High-tier wrist
        (entity_factory.marrow_cuff, 1),
        (entity_factory.pustule_bracelet, 1),

        # High-tier belt
        (entity_factory.tumor_laced_strap, 1),
        (entity_factory.bone_clasp_belt, 1),

        # High-tier legs
        (entity_factory.marrow_stitched_legwraps, 1),
        (entity_factory.tumorous_legplates, 1),
    ],

    6: [
        # High-tier gear and armor
        (entity_factory.fireball_scroll, 25),
        (entity_factory.chain_mail, 15),
        (entity_factory.thrall_reaver, 1),

        # Very rare items
        (entity_factory.pulsing_cranium, 1),
        (entity_factory.bloodstare_monocle, 1),
        (entity_factory.carotid_chain, 1),
        (entity_factory.oozing_pall, 1),
        (entity_factory.ossified_armlet, 1),
        (entity_factory.marrowstrap, 1),
        (entity_factory.pulsing_calfwraps, 1),
    ],

    8: [
        # Deep floor ultra-rare drops (endgame)
        (entity_factory.thrall_reaver, 2),
        (entity_factory.marrow_saw, 1),
        (entity_factory.knotted_mace, 1),

        # Legendary items
        (entity_factory.tumor_crowned_helm, 1),
        (entity_factory.eye_of_the_wyrm, 1),
        (entity_factory.ossified_torque, 1),
        (entity_factory.tendril_cloak, 1),
        (entity_factory.veinlace_wristband, 1),
        (entity_factory.bone_clasp_belt, 1),
        (entity_factory.tumorous_legplates, 1),
    ],
}


enemy_chances: Dict[int, List[Tuple[Entity, int]]] = {
    0: [
        (entity_factory.orc, 10),
        (entity_factory.rat, 60),
        (entity_factory.goblin, 60),
        (entity_factory.flayed_thrall, 8),
        (entity_factory.sinew_crawler, 6),
    ],
    2: [
        (entity_factory.zombie, 1),
        (entity_factory.eye_screamer, 4),
        (entity_factory.gnashing_swarm, 5),
    ],
    3: [
        (entity_factory.troll, 15),
        (entity_factory.howling_cyst, 5),
        (entity_factory.gnashing_swarm, 8),
    ],
    4: [
        (entity_factory.flesh_golem, 1),
        (entity_factory.vendor, 10),
        (entity_factory.howling_cyst, 6),
        (entity_factory.eye_screamer, 5),
    ],
    5: [
        (entity_factory.troll, 30),
        (entity_factory.vein_reaper, 10),
        (entity_factory.tumor_host, 8),
        (entity_factory.viscera_hound, 12),
    ],
    6: [
        (entity_factory.vein_reaper, 15),
        (entity_factory.tumor_host, 10),
        (entity_factory.viscera_hound, 15),
    ],
    7: [
        (entity_factory.troll, 60),
        (entity_factory.stitched_abomination, 10),
        (entity_factory.marrow_drinker, 12),
    ],
    8: [
        (entity_factory.stitched_abomination, 15),
        (entity_factory.marrow_drinker, 18),
    ],
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
            else:
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
