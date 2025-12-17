from __future__ import annotations

from typing import TYPE_CHECKING

import lzma
import pickle

from tcod.console import Console
from tcod.map import compute_fov

import exceptions

from game_map import GameMap, GameWorld
from message_log import MessageLog
import render_functions

if TYPE_CHECKING:
    from entity import Actor
    from game_map import GameMap


class Engine:
    game_map: GameMap
    game_world: GameWorld
    item_chances: dict
    enemy_chances: dict
    current_cheat_page: int = 0

    def __init__(self, player: Actor):
        self.message_log = MessageLog()
        self.mouse_location = (0, 0)
        self.player = player

    def handle_enemy_turns(self) -> None:
        for entity in set(self.game_map.actors) - {self.player}:
            if entity.ai:
                try:
                    entity.ai.perform()
                except exceptions.Impossible:
                    pass

    def update_fov(self) -> None:
        self.game_map.visible[:] = compute_fov(
            self.game_map.tiles["transparent"], (self.player.x, self.player.y), radius=8
        )
        self.game_map.explored |= self.game_map.visible

    def render(self, console: Console) -> None:
        self.game_map.render(console)
        self.message_log.render(console=console, x=21, y=45, width=40, height=5)
        render_functions.render_bar(
            console=console,
            current_value=self.player.fighter.hp,
            maximum_value=self.player.fighter.max_hp,
            total_width=20,
        )
        render_functions.render_tower_floor(
            console=console, tower_floor=self.game_world.current_floor, location=(0, 49)
        )
        render_functions.render_names_at_mouse_location(
            console=console, x=21, y=44, engine=self
        )

        if self.player.is_mage:
            render_functions.render_mana_bar(
                console=console,
                current_value=int(self.player.fighter.mana),
                maximum_value=self.player.fighter.max_mana,
                total_width=20,
            )
        elif self.player.is_rouge:
            render_functions.render_stamina_bar(
                console=console,
                current_value=self.player.fighter.stamina,
                maximum_value=self.player.fighter.max_stamina,
                total_width=20,
            )
        elif self.player.is_fighter:
            render_functions.render_mass_bar(
                console=console,
                current_value=self.player.fighter.mass,
                maximum_value=self.player.fighter.max_mass,
                total_width=20,
            )

    def save_as(self, filename: str) -> None:
        save_data = lzma.compress(pickle.dumps(self))
        with open(filename, "wb") as f:
            f.write(save_data)
