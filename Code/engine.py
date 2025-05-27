from typing import Set, Iterable, Any

from tcod.context import Context
from tcod.console import Console
from tcod.map import compute_fov

from actions import EscapeAction, MovementAction
from entity import Entity
from game_map import GameMap
from input_handlers import EventHandler

class Engine:
    def __init__(self, event_handler: EventHandler,game_map: GameMap, player: Entity):
        self.event_handler = event_handler
        self.game_map = game_map
        self.player = player
        self.update_fov()
    
    def handle_enemy_turns(self) -> None:
        for entity in self.game_map.entities - {self.player}:
            print(f'The {entity.name} wonders when it will get to take a real turn.')

    def handle_events(self, events : Iterable[Any]) -> None:
        for event in events:
            #create dispatcher
            action = self.event_handler.dispatch(event)
            #the event handler returns the class of correspoding event
            #if None event was not handeled
            if action is None:
                continue
            #if event is instance of action class
            #handle movement and escape
            action.perform(self, self.player)
            self.handle_enemy_turns()
            #this updates the player fov for durrent player position
            self.update_fov()

    def update_fov(self)->None:
        self.game_map.visible[:] = compute_fov(
            self.game_map.tiles["transparent"],
            (self.player.x, self.player.y),
            radius=8
        )
        self.game_map.explored |= self.game_map.visible

    def render(self, console: Console, context: Context) -> None:
        self.game_map.render(console)

        context.present(console)
        console.clear()