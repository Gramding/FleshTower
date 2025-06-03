from __future__ import annotations
import os
import copy
from typing import Optional, TYPE_CHECKING, Tuple, Callable, Union
import tcod
import actions
from actions import Action, BumpAction, WaitAction, PickupAction
import color
import exceptions
import libtcodpy

if TYPE_CHECKING:
    from engine import Engine
    from entity import Item
    from components.spells import Spell

MOVE_KEYS = {
    # Arrow keys.
    tcod.event.KeySym.UP: (0, -1),
    tcod.event.KeySym.DOWN: (0, 1),
    tcod.event.KeySym.LEFT: (-1, 0),
    tcod.event.KeySym.RIGHT: (1, 0),
    tcod.event.KeySym.HOME: (-1, -1),
    tcod.event.KeySym.END: (-1, 1),
    tcod.event.KeySym.PAGEUP: (1, -1),
    tcod.event.KeySym.PAGEDOWN: (1, 1),
    # Numpad keys.
    tcod.event.KeySym.KP_1: (-1, 1),
    tcod.event.KeySym.KP_2: (0, 1),
    tcod.event.KeySym.KP_3: (1, 1),
    tcod.event.KeySym.KP_4: (-1, 0),
    tcod.event.KeySym.KP_6: (1, 0),
    tcod.event.KeySym.KP_7: (-1, -1),
    tcod.event.KeySym.KP_8: (0, -1),
    tcod.event.KeySym.KP_9: (1, -1),
    # Vi keys.
    tcod.event.KeySym.h: (-1, 0),
    tcod.event.KeySym.j: (0, 1),
    tcod.event.KeySym.k: (0, -1),
    tcod.event.KeySym.l: (1, 0),
    tcod.event.KeySym.y: (-1, -1),
    tcod.event.KeySym.u: (1, -1),
    tcod.event.KeySym.b: (-1, 1),
    tcod.event.KeySym.n: (1, 1),
}

WAIT_KEYS = {
    tcod.event.KeySym.PERIOD,
    tcod.event.KeySym.KP_5,
    tcod.event.KeySym.CLEAR,
}

CONFIRM_KEYS = {
    tcod.event.KeySym.RETURN,
    tcod.event.KeySym.KP_ENTER,
}

ActionOrHandler = Union[Action, "BaseEventHandler"]


def get_target_vendor(engine: Engine) -> any:
    target = engine.game_map.get_actor_at_location(engine.player.x, engine.player.y - 1)
    if not target:
        target = engine.game_map.get_actor_at_location(
            engine.player.x, engine.player.y + 1
        )
    if not target:
        target = engine.game_map.get_actor_at_location(
            engine.player.x + 1, engine.player.y
        )
    if not target:
        target = engine.game_map.get_actor_at_location(
            engine.player.x - 1, engine.player.y
        )
    return target


class BaseEventHandler(tcod.event.EventDispatch[ActionOrHandler]):
    def handle_events(self, event: tcod.event.Event) -> BaseEventHandler:
        """Handle an event and return the next active event handler."""
        state = self.dispatch(event)
        if isinstance(state, BaseEventHandler):

            return state
        assert not isinstance(state, Action), f"{self!r} can not handle actions."
        return self

    def on_render(self, console: tcod.Console) -> None:
        raise NotImplementedError()

    def ev_quit(self, event: tcod.event.Quit) -> Optional[Action]:
        raise SystemExit()


class PopupMessage(BaseEventHandler):
    def __init__(self, parent_handler: BaseEventHandler, text: str):
        self.parent = parent_handler
        self.text = text

    def on_render(self, console):
        self.parent.on_render(console)
        console.rgb["fg"] //= 8
        console.rgb["bg"] //= 8

        console.print(
            console.width // 2,
            console.height // 2,
            self.text,
            fg=color.white,
            bg=color.black,
            alignment=libtcodpy.CENTER,
        )

    def ev_keydown(self, event):
        return self.parent


class EventHandler(BaseEventHandler):
    def __init__(self, engine: Engine):
        self.engine = engine

    def handle_events(self, event):
        action_or_state = self.dispatch(event)
        if isinstance(action_or_state, BaseEventHandler):
            return action_or_state
        if self.handle_action(action_or_state):
            if not self.engine.player.is_alive:
                return GameOverEventHandler(self.engine)
            elif self.engine.player.level.requires_level_up:
                return LevelUpEventHandler(self.engine)
            return MainGameEventHandler(self.engine)
        return self

    def handle_action(self, action: Optional[Action]) -> bool:
        """Handle actions returned from event methods.
        Returns True if the action will advance a turn.
        """
        if action is None:
            return False

        try:
            action.perform()
        except exceptions.Impossible as exc:
            self.engine.message_log.add_message(exc.args[0], color.impossible)
            return False  # Skip enemy turn on exceptions.
        self.engine.handle_enemy_turns()
        self.engine.update_fov()
        return True

    def ev_mousemotion(self, event: tcod.event.MouseMotion) -> None:
        if self.engine.game_map.in_bounds(event.tile.x, event.tile.y):
            self.engine.mouse_location = event.tile.x, event.tile.y

    def on_render(self, console: tcod.Console) -> None:
        self.engine.render(console)


class AskUserEventHandler(EventHandler):

    def ev_keydown(self, event) -> Optional[ActionOrHandler]:
        if event.sym in {  # Ignore modifier keys.
            tcod.event.KeySym.LSHIFT,
            tcod.event.KeySym.RSHIFT,
            tcod.event.KeySym.LCTRL,
            tcod.event.KeySym.RCTRL,
            tcod.event.KeySym.LALT,
            tcod.event.KeySym.RALT,
        }:
            return None
        return self.on_exit()

    def ev_mousebuttondown(self, event) -> Optional[ActionOrHandler]:
        return self.on_exit()

    def on_exit(self) -> Optional[ActionOrHandler]:
        return MainGameEventHandler(self.engine)


class CharacterScreenEventHandler(AskUserEventHandler):
    TITLE = "Stats"

    def on_render(self, console):
        super().on_render(console)
        if self.engine.player.x <= 30:
            x = 40
        else:
            x = 0

        y = 0

        width = len(self.TITLE) + 30

        console.draw_frame(
            x=x,
            y=y,
            width=width,
            height=8,
            clear=True,
            fg=(255, 255, 255),
            bg=(0, 0, 0),
            title=self.TITLE,
        )
        console.print(
            x=x + 1, y=y + 1, string=f"Level: {self.engine.player.level.current_level}"
        )
        console.print(
            x=x + 1, y=y + 2, string=f"XP: {self.engine.player.level.current_xp}"
        )
        console.print(
            x=x + 1,
            y=y + 3,
            string=f"XP for next Level: {self.engine.player.level.xp_to_next_level}",
        )

        console.print(
            x=x + 1, y=y + 4, string=f"Attack: {self.engine.player.fighter.power}"
        )
        console.print(
            x=x + 1, y=y + 5, string=f"Defense: {self.engine.player.fighter.defense}"
        )
        console.print(x=x + 1, y=y + 6, string=f"Organs: {self.engine.player.currency}")


class ConsumptionScreenEventHandler(AskUserEventHandler):
    TITLE = "Things Consumed"

    def on_render(self, console):
        super().on_render(console)
        number_of_consumption_attr = len(self.engine.player.logbook.book)
        if number_of_consumption_attr > 0:
            height = number_of_consumption_attr + 2
        else:
            height = 3

        if self.engine.player.x <= 30:
            x = 40
        else:
            x = 0

        y = 0

        width = len(self.TITLE) + 12

        console.draw_frame(
            x=x,
            y=y,
            width=width,
            height=height,
            title=self.TITLE,
            clear=True,
            fg=(255, 255, 255),
            bg=(0, 0, 0),
        )
        if number_of_consumption_attr > 0:

            for i, name in enumerate(self.engine.player.logbook.book):
                print = name.replace("remains of ", "").capitalize()
                console.print(
                    x + 1,
                    y + i + 1,
                    f"{print}: {self.engine.player.logbook.book[name]}",
                )
        else:
            console.print(x + 1, y + 1, "(Empty)")


class LevelUpEventHandler(AskUserEventHandler):
    TITLE = "Level Up"

    def on_render(self, console):
        super().on_render(console)
        if self.engine.player.x <= 30:
            x = 40
        else:
            x = 0

        console.draw_frame(
            x=x,
            y=0,
            width=35,
            height=12,
            title=self.TITLE,
            clear=True,
            fg=(255, 255, 255),
            bg=(0, 0, 0),
        )
        console.print(x=x + 1, y=1, string="The tower grants you power")
        console.print(x=x + 1, y=2, string="Select the towers blessing")
        console.print(
            x=x + 1,
            y=4,
            string=f"a) Constitution (+20 HP, from {self.engine.player.fighter.max_hp})",
        )
        console.print(
            x=x + 1,
            y=5,
            string=f"b) Strength (+1 attack, from {self.engine.player.fighter.power})",
        )
        console.print(
            x=x + 1,
            y=6,
            string=f"c) Agility (+1 defense, from {self.engine.player.fighter.defense})",
        )
        if self.engine.player.is_mage:
            console.print(
                x=x + 1,
                y=7,
                string=f"d) Mana (+10 mana, from {self.engine.player.fighter.max_mana})",
            )

    def ev_keydown(self, event):
        player = self.engine.player
        key = event.sym
        index = key - tcod.event.KeySym.a

        if 0 <= index <= 3:
            if index == 0:
                player.level.increase_max_hp()
            elif index == 1:
                player.level.increase_power()
            elif index == 2:
                player.level.increase_defense()
            elif index == 3 and player.is_mage:
                player.level.increase_max_mana()
        else:
            self.engine.message_log.add_message("Invalide selection", color.invalid)

            return None
        return super().ev_keydown(event)

    def ev_mousebuttondown(self, event):
        # none disallows player to exit via mouseclick
        # level up is mandatory
        return None


class InventoryEventHandler(AskUserEventHandler):
    TITLE = "<missing title>"

    def on_render(self, console):
        super().on_render(console)
        number_of_items_in_inventory = len(self.engine.player.inventory.items)
        height = number_of_items_in_inventory + 2

        if height <= 3:
            height = 3

        if self.engine.player.x <= 30:
            x = 40
        else:
            x = 0

        y = 0

        width = len(self.TITLE) + 10

        console.draw_frame(
            x=x,
            y=y,
            width=width,
            height=height,
            title=self.TITLE,
            clear=True,
            fg=(255, 255, 255),
            bg=(0, 0, 0),
        )

        if number_of_items_in_inventory > 0:
            for i, item in enumerate(self.engine.player.inventory.items):
                item_key = chr(ord("a") + i)
                is_equipped = self.engine.player.equipment.item_is_equipped(item)

                item_string = f"({item_key}) {item.name}"

                if is_equipped:
                    item_string = f"{item_string} (E)"

                console.print(x + 1, y + i + 1, item_string)
        else:
            console.print(x + 1, y + 1, "(Empty)")

    def ev_keydown(self, event) -> Optional[ActionOrHandler]:
        player = self.engine.player
        key = event.sym
        index = key - tcod.event.KeySym.a

        if 0 <= index <= 26:
            try:
                selected_item = player.inventory.items[index]
            except IndexError:
                self.engine.message_log.add_message(
                    "Invalid inventory slot.", color.invalid
                )
                return None
            return self.on_item_selected(selected_item)
        return super().ev_keydown(event)

    def on_item_selected(self, item: Item) -> Optional[ActionOrHandler]:
        raise NotImplemented()


class InventoryActivateHandler(InventoryEventHandler):
    TITLE = "Select item to use"

    def on_item_selected(self, item: Item) -> Optional[ActionOrHandler]:
        if item.consumable:
            # Return action for the selected item
            return item.consumable.get_action(self.engine.player)
        elif item.equippable:
            return actions.EquipAction(self.engine.player, item)
        else:
            return None


class InventoryDropHandler(InventoryEventHandler):
    TITLE = "Select item to drop"

    def on_item_selected(self, item) -> Optional[ActionOrHandler]:
        return actions.DropItem(self.engine.player, item)


class SpellBookEventHandler(AskUserEventHandler):
    def __init__(self, engine):
        super().__init__(engine)

    def on_render(self, console):
        super().on_render(console)
        number_of_spells_in_book = len(self.engine.player.spellbook.spells)
        height = number_of_spells_in_book + 2

        if height <= 3:
            height = 3

        if self.engine.player.x <= 30:
            x = 40
        else:
            x = 0

        y = 0

        width = len(self.TITLE) + 6

        console.draw_frame(
            x=x,
            y=y,
            width=width,
            height=height,
            title=self.TITLE,
            clear=True,
            fg=(255, 255, 255),
            bg=(0, 0, 0),
        )

        if number_of_spells_in_book > 0:
            for i, spell in enumerate(self.engine.player.spellbook.spells):
                spell_key = chr(ord("a") + i)

                spell_string = f"({spell_key}) {spell.name}"

                console.print(x + 1, y + i + 1, spell_string)
        else:
            console.print(x + 1, y + 1, "(Empty)")

    def ev_keydown(self, event):
        player = self.engine.player
        key = event.sym
        index = key - tcod.event.KeySym.a

        if 0 <= index <= 26:
            try:
                selected_spell = player.spellbook.spells[index]
            except IndexError:
                self.engine.message_log.add_message(
                    "Invalid page in spell book.", color.invalid
                )
                return None
            return self.on_spell_selected(selected_spell)
        return super().ev_keydown(event)


class SpellBookActivateHandler(SpellBookEventHandler):
    TITLE = "Select spell to use"

    def on_spell_selected(self, spell: Spell) -> Optional[ActionOrHandler]:
        return spell.activate()


class ShopHandler(AskUserEventHandler):
    def __init__(self, engine, target: any):
        self.target = target
        super().__init__(engine)

    def on_render(self, console):

        super().on_render(console)
        number_of_items_in_shop = len(self.target.inventory.items)
        height = number_of_items_in_shop + 2

        if height <= 3:
            height = 3

        if self.engine.player.x <= 30:
            x = 40
        else:
            x = 0

        y = 0

        width = len(self.TITLE) + 10

        console.draw_frame(
            x=x,
            y=y,
            width=width,
            height=height,
            title=self.TITLE,
            clear=True,
            fg=(255, 255, 255),
            bg=(0, 0, 0),
        )

        if number_of_items_in_shop > 0:
            for i, item in enumerate(self.target.inventory.items):
                spell_key = chr(ord("a") + i)

                item_string = f"({spell_key}) {item.name}"

                console.print(x + 1, y + i + 1, item_string)
        else:
            console.print(x + 1, y + 1, "(Empty)")

    def ev_keydown(self, event):
        player = self.engine.player
        key = event.sym
        index = key - tcod.event.KeySym.a

        if 0 <= index <= 26:
            try:
                seleted_item = self.target.inventory.items[index]
            except IndexError:
                self.engine.message_log.add_message(
                    "What? I don't have that!", color.invalid
                )
                return None
            return self.on_item_selected(seleted_item)
        return super().ev_keydown(event)


class ShopActivateHandler(ShopHandler):
    TITLE = "Select item to buy"

    def on_item_selected(self, item: Item) -> Optional[ActionOrHandler]:
        if self.engine.player.currency >= item.price:
            i_tem = copy.deepcopy(item)

            i_tem.parent = self.engine.player.inventory
            self.engine.player.inventory.items.append(i_tem)
            self.target.inventory.items.remove(item)
            self.engine.player.currency -= item.price
        else:
            self.engine.message_log.add_message(
                f"You're too poor are you not? This {item.name} costs {item.price} organs"
            )
        return  # item.activate()


class SelectIndexHandler(AskUserEventHandler):
    def __init__(self, engine):
        super().__init__(engine)
        player = self.engine.player
        engine.mouse_location = player.x, player.y

    def on_render(self, console):
        super().on_render(console)
        x, y = self.engine.mouse_location
        console.rgb["bg"][x, y] = color.white
        console.rgb["fg"][x, y] = color.black

    def ev_keydown(self, event) -> Optional[ActionOrHandler]:
        key = event.sym
        if key in MOVE_KEYS:
            modifier = 1
            if event.mod & (tcod.event.KeySym.LSHIFT | tcod.event.KeySym.RSHIFT):
                modifier *= 5
            if event.mod & (tcod.event.KeySym.LCTRL | tcod.event.KeySym.RCTRL):
                modifier *= 10
            if event.mod & (tcod.event.KeySym.LALT | tcod.event.KeySym.RALT):
                modifier *= 20

            x, y = self.engine.mouse_location

            dx, dy = MOVE_KEYS[key]
            x += dx * modifier
            y += dy * modifier
            x = max(0, min(x, self.engine.game_map.width - 1))
            y = max(0, min(y, self.engine.game_map.height - 1))
            self.engine.mouse_location = x, y
            return None
        elif key in CONFIRM_KEYS:
            return self.on_index_selected(*self.engine.mouse_location)

        return super().ev_keydown(event)

    def ev_mousebuttondown(self, event) -> Optional[ActionOrHandler]:
        if self.engine.game_map.in_bounds(*event.tile):
            if event.button == 1:
                return self.on_index_selected(*event.tile)
        return super().ev_mousebuttondown(event)

    def on_index_selected(self, x: int, y: int) -> Optional[ActionOrHandler]:
        raise NotImplementedError()


class LookHandler(SelectIndexHandler):
    def on_index_selected(self, x, y) -> MainGameEventHandler:
        return MainGameEventHandler(self.engine)


class SingleRangedAttackHandler(SelectIndexHandler):
    def __init__(
        self, engine, callback: Callable[[Tuple[int, int]]]
    ) -> Optional[Action]:
        super().__init__(engine)
        self.callback = callback

    def on_index_selected(self, x, y) -> Optional[Action]:
        return self.callback((x, y))


class AreaRangedAttackHandler(SelectIndexHandler):
    def __init__(
        self,
        engine: Engine,
        radius: int,
        callback: Callable[[Tuple[int, int]], Optional[Action]],
    ):
        super().__init__(engine)
        self.radius = radius
        self.callback = callback

    def on_render(self, console):
        super().on_render(console)
        x, y = self.engine.mouse_location
        console.draw_frame(
            x=x - self.radius - 1,
            y=y - self.radius - 1,
            width=self.radius**2,
            height=self.radius**2,
            fg=color.red,
            clear=False,
        )

    def on_index_selected(self, x, y):
        return self.callback((x, y))


class MainGameEventHandler(EventHandler):
    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        action: Optional[Action] = None

        key = event.sym
        modifier = event.mod

        player = self.engine.player

        if key == tcod.event.KeySym.PERIOD and modifier & (
            tcod.event.KeySym.LSHIFT | tcod.event.KeySym.RSHIFT
        ):
            return actions.TakeStairsAction(player)

        if key == tcod.event.KeySym.c and modifier & (
            tcod.event.KeySym.LSHIFT | tcod.event.KeySym.RSHIFT
        ):
            return actions.ConsumeCorpseAction(player)

        if key == tcod.event.KeySym.l:
            return ConsumptionScreenEventHandler(self.engine)

        if key == tcod.event.KeySym.p and self.engine.player.is_mage:
            return SpellBookActivateHandler(self.engine)
        target = get_target_vendor(engine=self.engine)
        if key == tcod.event.KeySym.t and target and "Organ" in target.name:
            return ShopActivateHandler(engine=self.engine, target=target)

        if key in MOVE_KEYS:
            dx, dy = MOVE_KEYS[key]
            action = BumpAction(player, dx, dy)
        elif key in WAIT_KEYS:
            action = WaitAction(player)

        elif key == tcod.event.KeySym.ESCAPE:
            raise SystemExit()
        elif key == tcod.event.KeySym.v:
            return HistoryViewer(self.engine)
        elif key == tcod.event.KeySym.g:
            action = PickupAction(player)
        elif key == tcod.event.KeySym.i:
            return InventoryActivateHandler(self.engine)
        elif key == tcod.event.KeySym.d:
            return InventoryDropHandler(self.engine)
        elif key == tcod.event.KeySym.c:
            return CharacterScreenEventHandler(self.engine)
        elif key == tcod.event.KeySym.SLASH:
            return LookHandler(self.engine)

        # No valid key was pressed
        # action = None
        return action


class GameOverEventHandler(EventHandler):
    def on_quit(self) -> None:
        if os.path.exists("savegame.sav"):
            os.remove("savegame.sav")
        raise exceptions.QuitWithoutSaving()

    def ev_quit(self, event):
        self.on_quit()

    def ev_keydown(self, event: tcod.event.KeyDown) -> None:
        if event.sym == tcod.event.KeySym.ESCAPE:
            self.on_quit()


CURSOR_Y_KEYS = {
    tcod.event.KeySym.UP: -1,
    tcod.event.KeySym.DOWN: 1,
    tcod.event.KeySym.PAGEUP: -10,
    tcod.event.KeySym.PAGEDOWN: 10,
}


class HistoryViewer(EventHandler):
    def __init__(self, engine):
        super().__init__(engine)
        self.log_lenght = len(engine.message_log.messages)
        self.cursor = self.log_lenght - 1

    def on_render(self, console: tcod.console) -> None:
        super().on_render(console)
        log_console = tcod.console.Console(console.width - 6, console.height - 6)
        log_console.print_box(
            0, 0, log_console.width, 1, "|Message history|", alignment=libtcodpy.CENTER
        )

        self.engine.message_log.render_messages(
            log_console,
            1,
            1,
            log_console.width - 2,
            log_console.height - 2,
            self.engine.message_log.messages[: self.cursor + 1],
        )
        log_console.blit(console, 3, 3)

    def ev_keydown(self, event) -> Optional[ActionOrHandler]:
        if event.sym in CURSOR_Y_KEYS:
            adjust = CURSOR_Y_KEYS[event.sym]
            if adjust < 0 and self.cursor == 0:
                self.cursor = self.log_lenght - 1
            elif adjust > 0 and self.cursor == self.log_lenght - 1:
                self.cursor = 0
            else:
                self.cursor = max(0, min(self.cursor + adjust, self.log_lenght - 1))
        elif event.sym == tcod.event.KeySym.HOME:
            self.cursor = 0
        elif event.sym == tcod.event.KeySym.END:
            self.cursor = self.log_lenght - 1
        else:
            return MainGameEventHandler(self.engine)
        return None


class CunsumptionEventHandler(EventHandler):
    def __init__(self, engine):
        super().__init__(engine)
