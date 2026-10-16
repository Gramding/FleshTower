from __future__ import annotations
import math
import os
import copy
import textwrap
from typing import Optional, TYPE_CHECKING, Tuple, Callable, Union
import tcod
import actions
from actions import Action, BumpAction, WaitAction, PickupAction
import color
import exceptions
import libtcodpy
from numpy import array_split
from components.dialouge_parser import quest_key


from components.settings import (
    CHEATS,
    GENERAL_CHEATS,
    GENERAL_CHEAT_ACTIVATIONS,
    PlayerClass,
)
import components.affix as affix

# from procgen import item_chances, enemy_chances
# from components.procgen_chances import item_chances

if TYPE_CHECKING:
    from engine import Engine
    from entity import Item, Actor
    from components.spells import Spell

MOVE_KEYS = {
    # Arrow keys.
    100: (0, -1),
    101: (0, 1),
    102: (-1, 0),
    103: (1, 0),
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
    def __init__(
        self, parent_handler: BaseEventHandler, text: str, halved: bool, alignment
    ):
        self.parent = parent_handler
        self.text = text
        self.halved = halved
        self.alignment = alignment

    def on_render(self, console):
        self.parent.on_render(console)
        console.rgb["fg"] //= 8
        console.rgb["bg"] //= 8
        width = console.width
        height = console.height
        if self.halved:
            width = width // 2
            height = height // 2
        else:
            width = int(width / 2)
            height = height // 5

        console.print(
            width,
            height,
            self.text,
            fg=color.white,
            bg=color.black,
            alignment=self.alignment,
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
            if getattr(self.engine.game_world, "campaign_complete", False):
                return CampaignVictoryHandler(self.engine)
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
        if self.engine.game_map.in_bounds(int(event.tile.x), int(event.tile.y)):
            self.engine.mouse_location = int(event.tile.x), int(event.tile.y)

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
            tcod.event.KeySym.PAGEUP,
            tcod.event.KeySym.PAGEDOWN,
        }:
            return None
        return self.on_exit()

    def ev_mousebuttondown(self, event) -> Optional[ActionOrHandler]:
        return self.on_exit()

    def on_exit(self) -> Optional[ActionOrHandler]:
        return MainGameEventHandler(self.engine)


class CharacterScreenEventHandler(AskUserEventHandler):
    TITLE = "Stats"

    def __init__(self, engine):
        super().__init__(engine)
        self.log_lenght = len(engine.affixManager.message_log.messages)
        self.cursor = self.log_lenght - 1

    def on_render(self, console: tcod.console.Console):
        super().on_render(console)
        AFFIX_DIR_LEN = len(self.engine.affixManager.affixes)
        affix_max_len = console.height - 26

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
            height=14 + affix_max_len,
            clear=True,
            fg=(255, 255, 255),
            bg=(0, 0, 0),
            title=self.TITLE,
        )
        level = f"Level: {self.engine.player.level.current_level}"
        console.print(x=x + 1, y=y + 1, text=level)
        console.print(
            x=(x + 1) + len(level) + 5,
            y=y + 1,
            text=f"Organs: {self.engine.player.currency}",
        )

        # display class name in stat screen
        console.print(
            x=(x + 1),
            y=y + 2,
            text=f"Class: {self.engine.player.class_name}",
        )
        from render_functions import render_xp_bar

        render_xp_bar(
            console=console,
            current_value=self.engine.player.level.current_xp,
            maximum_value=self.engine.player.level.xp_to_next_level,
            total_width=width - 2,
            x=x + 1,
            y=y + 3,
        )

        console.draw_rect(
            x=x + 1,
            y=5,
            width=width - 2,
            height=1,
            ch=ord("─"),
            fg=(255, 255, 255),
            bg=(0, 0, 0),
            bg_blend=libtcodpy.BKGND_MULTIPLY,
        )

        self.engine.affixManager.message_log.render_messages(
            console,
            x + 1,
            6,
            console.width - 2,
            24,
            self.engine.affixManager.message_log.messages[: self.cursor + 1],
        )

        console.print(
            x=x + 1,
            y=5,
            text="┤Affixes├",
            alignment=libtcodpy.CENTER,
            width=width - 2,
            height=1,
        )

        console.draw_rect(
            x=x + 1,
            y=6 + affix_max_len,
            width=width - 2,
            height=1,
            ch=ord("─"),
            fg=(255, 255, 255),
            bg=(0, 0, 0),
            bg_blend=libtcodpy.BKGND_MULTIPLY,
        )
        console.print(
            x=x + 1,
            y=6 + affix_max_len,
            text="┤Behavioral Deviations├",
            alignment=libtcodpy.CENTER,
            width=width - 2,
            height=1,
        )
        text = "Meele Damage"
        console.print(
            x=x + 1,
            y=8 + affix_max_len,
            text=f"{text:<20}: {self.engine.player.fighter.power}",
        )
        text = "Defense"
        console.print(
            x=x + 1,
            y=9 + affix_max_len,
            text=f"{text:<20}: {self.engine.player.fighter.defense}",
        )
        text = "Spell Damage"
        console.print(
            x=x + 1,
            y=10 + affix_max_len,
            text=f"{text:<20}: {self.engine.player.fighter.spell_damage_bonus}",
        )
        text = "Price Discount"
        console.print(
            x=x + 1,
            y=11 + affix_max_len,
            text=f"{text:<20}: {self.engine.player.fighter.price_discount}",
        )
        text = "Attack Count"
        console.print(
            x=x + 1,
            y=12 + affix_max_len,
            text=f"{text:<20}: {self.engine.player.fighter.attack_count}",
        )

    def ev_keydown(self, event):
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
        width = len(self.TITLE) + 20

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
                    f"{print:<30}: {self.engine.player.logbook.book[name]}",
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
            width=40,
            height=13,
            title=self.TITLE,
            clear=True,
            fg=(255, 255, 255),
            bg=(0, 0, 0),
        )
        console.print(x=x + 1, y=1, string="The tower grants you power")

        self.affix = random_affix = self.engine.affixManager.rand_affix()
        self.engine.player.fighter.reset_self()

        console.print(
            x=x + 1,
            y=4,
            string=random_affix.AFFIX_NAME,
            fg=random_affix.AFFIX_COLOR.value,
        )

    def ev_keydown(self, event):
        self.engine.affixManager.gain_affix(self.affix)
        self.engine.affixManager.derive_affixes()
        self.engine.player.level.increase_level()

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
        index = key - tcod.event.KeySym.A

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
        raise NotImplementedError()


class InventoryActivateHandler(InventoryEventHandler):
    TITLE = "Select item to use"

    def on_item_selected(self, item: Item) -> Optional[ActionOrHandler]:
        if getattr(item, "lore", None) is not None:
            return ReadingScreen(self.engine, item)
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
    TITLE = "Select spell to use"

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
        index = key - tcod.event.KeySym.A

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
    def on_spell_selected(self, spell: Spell) -> Optional[ActionOrHandler]:
        spell.activate()
        return actions.CastSpell(self.engine.player)


class ShopHandler(AskUserEventHandler):
    TITLE = "Select item to buy"

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
        key = event.sym
        index = key - tcod.event.KeySym.A

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
    def on_item_selected(self, item: Item) -> Optional[ActionOrHandler]:
        # player price discount from Visceral Influence -> Flesh Bargain taken into acount
        real_price = item.price - (
            item.price * (self.engine.player.fighter.price_discount / 100)
        )
        real_price = int(real_price)
        if self.engine.player.currency >= item.price:
            i_tem = copy.deepcopy(item)

            i_tem.parent = self.engine.player.inventory
            self.engine.player.inventory.items.append(i_tem)
            self.target.inventory.items.remove(item)
            self.engine.player.currency -= real_price
            self.engine.message_log.add_message(
                f"You buy {item.name} for {real_price} organs"
            )
        else:
            self.engine.message_log.add_message(
                f"You're too poor are you not? This {item.name} costs {real_price} organs"
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
        x = int(x)
        y = int(y)
        if x >= 80:
            x = 0
        if y >= 50:
            y = 0
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


def get_event_by_id(id: int):
    from components.settings import KEYBINDS

    currentKey = {}

    for section in KEYBINDS:
        for key in KEYBINDS[section]:
            if KEYBINDS[section][key]["ID"] == id:
                currentKey = KEYBINDS[section][key]
    return currentKey


# readable names for keys whose KeySym name is not what is printed on the key
KEY_LABELS = {
    "PERIOD": ".", "COMMA": ",", "SLASH": "/", "SEMICOLON": ";", "APOSTROPHE": "'",
    "MINUS": "-", "EQUALS": "=", "LEFTBRACKET": "[", "RIGHTBRACKET": "]",
    "BACKSLASH": "\\", "GRAVE": "`", "ESCAPE": "Esc", "RETURN": "Enter",
    "KP_ENTER": "Enter", "PAGEUP": "PgUp", "PAGEDOWN": "PgDn",
}


def mod_label(mod) -> str:
    mod = tcod.event.Modifier(mod)
    parts = []
    if mod & CTRL:
        parts.append("Ctrl")
    if mod & (tcod.event.Modifier.LALT | tcod.event.Modifier.RALT):
        parts.append("Alt")
    if mod & SHIFT:
        parts.append("Shift")
    return " + ".join(parts)


def key_label(key, mod=tcod.event.Modifier.NONE) -> str:
    """e.g. 'Shift + .' for the take stairs bind."""
    name = tcod.event.KeySym(key).name
    if len(name) == 2 and name[0] == "N" and name[1].isdigit():
        text = name[1]  # number row keys are called N1, N2, ...
    else:
        text = KEY_LABELS.get(name, name if len(name) == 1 else name.title())
    prefix = mod_label(mod)
    return f"{prefix} + {text}" if prefix else text


class KeybindScreen(BaseEventHandler):
    """Lists every keybind, read from KEYBINDS so it always shows the real keys."""

    WIDTH = 46

    def __init__(self, parent: BaseEventHandler):
        self.parent = parent
        self.lines = self.build_lines()

    @staticmethod
    def build_lines():
        from components.settings import KEYBINDS

        lines = []  # (text, colour)
        for section, binds in KEYBINDS.items():
            lines.append((section, color.menu_title))
            for bind in binds.values():
                # for movement MOD is the rogue sprint, not part of the key
                mod = tcod.event.Modifier.NONE if section == "Movement" else bind["MOD"]
                lines.append((f"  {key_label(bind['KEY'], mod):<14}{bind['NAME']}", color.menu_text))
            if section == "Movement" and binds:
                sprint = mod_label(next(iter(binds.values()))["MOD"])
                if sprint:
                    lines.append((f"  {sprint + ' + move':<14}Sprint (Rogue)", color.menu_text))
            lines.append(("", color.menu_text))
        lines.append(("Other", color.menu_title))
        lines.append((f"  {'/':<14}Look around", color.menu_text))
        lines.append((f"  {'H':<14}Keybinds", color.menu_text))
        return lines

    def on_render(self, console):
        self.parent.on_render(console)
        dim(console)
        height = len(self.lines) + 5
        x, y = draw_box(console, self.WIDTH, height, "Keybinds")
        for i, (text, fg) in enumerate(self.lines):
            console.print(x + 2, y + 2 + i, text[: self.WIDTH - 4], fg=fg)
        console.print(x + 2, y + height - 2, "[Esc] close", fg=color.impossible)

    def ev_keydown(self, event):
        if event.sym in CONFIRM_KEYS or event.sym in (
            tcod.event.KeySym.ESCAPE,
            tcod.event.KeySym.H,
            tcod.event.KeySym.K,
        ):
            return self.parent
        return None


class MainGameEventHandler(EventHandler):
    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        action: Optional[Action] = None

        key = event.sym
        modifier = event.mod
        # print(f"Key:{key}\nMod:{modifier}")

        if modifier == tcod.event.Modifier.NUM:
            modifier = tcod.event.Modifier.NONE
        if modifier == tcod.event.Modifier(4097):
            modifier = tcod.event.Modifier.LSHIFT

        player = self.engine.player
        c_event = get_event_by_id(1)
        if key == tcod.event.KeySym(c_event["KEY"]) and modifier == tcod.event.Modifier(
            c_event["MOD"]
        ):
            return actions.TakeStairsAction(player)
        c_event = get_event_by_id(2)
        if key == tcod.event.KeySym(c_event["KEY"]) and modifier == tcod.event.Modifier(
            c_event["MOD"]
        ):
            return actions.ConsumeCorpseAction(player)
        c_event = get_event_by_id(11)
        if key == tcod.event.KeySym(c_event["KEY"]) and modifier == tcod.event.Modifier(
            c_event["MOD"]
        ):
            return ConsumptionScreenEventHandler(self.engine)

        c_event = get_event_by_id(10)
        if key == tcod.event.KeySym(c_event["KEY"]) and modifier == tcod.event.Modifier(
            c_event["MOD"]
        ):
            return SpellBookActivateHandler(self.engine)
        target = get_target_vendor(engine=self.engine)
        c_event = get_event_by_id(3)
        if (
            key == tcod.event.KeySym(c_event["KEY"])
            and modifier == tcod.event.Modifier(c_event["MOD"])
            and target
        ):
            if getattr(target, "dialogue", None) is not None:
                return DialogueScreen(self.engine, target)
            if "Organ" in target.name:
                return ShopActivateHandler(engine=self.engine, target=target)
            self.engine.message_log.add_message(
                f"{target.name} has nothing to say.", color.impossible
            )
            return None

        for movement_id in range(100, 104):
            c_event = get_event_by_id(movement_id)
            if c_event["ID"] in MOVE_KEYS and key == c_event["KEY"]:
                dx, dy = MOVE_KEYS[c_event["ID"]]
                # if player ist rouge they can sprint this consumes stamina. in order to sprint the input is multiplied by 2
                if (
                    self.engine.player.player_class == PlayerClass.ROUGE
                    and tcod.event.Modifier(c_event["MOD"]) in modifier
                    and self.engine.player.fighter.stamina >= 2
                ):
                    dx = dx * 2
                    dy = dy * 2
                    # stamina is now handlede by the bump action
                    # self.engine.player.fighter.stamina -= 2
                elif (
                    self.engine.player.fighter.stamina
                    < self.engine.player.fighter.max_stamina
                ):
                    # if player is not sprinting they regain 1 stamina per movement
                    self.engine.player.fighter.stamina += 1
                return BumpAction(player, dx, dy)
            elif key in WAIT_KEYS:
                return WaitAction(player)

        c_event = get_event_by_id(5)
        if key == tcod.event.KeySym(c_event["KEY"]) and modifier == tcod.event.Modifier(
            c_event["MOD"]
        ):
            raise SystemExit()

        c_event = get_event_by_id(12)
        if key == tcod.event.KeySym(c_event["KEY"]) and modifier == tcod.event.Modifier(
            c_event["MOD"]
        ):
            return HistoryViewer(self.engine)

        c_event = get_event_by_id(4)
        if key == tcod.event.KeySym(c_event["KEY"]) and modifier == tcod.event.Modifier(
            c_event["MOD"]
        ):
            action = PickupAction(player)

        c_event = get_event_by_id(6)
        if key == tcod.event.KeySym(c_event["KEY"]) and modifier == tcod.event.Modifier(
            c_event["MOD"]
        ):
            return InventoryActivateHandler(self.engine)

        c_event = get_event_by_id(7)
        if key == tcod.event.KeySym(c_event["KEY"]) and modifier == tcod.event.Modifier(
            c_event["MOD"]
        ):
            return InventoryDropHandler(self.engine)

        c_event = get_event_by_id(8)
        if key == tcod.event.KeySym(c_event["KEY"]) and modifier == tcod.event.Modifier(
            c_event["MOD"]
        ):
            return CharacterScreenEventHandler(self.engine)
        if key == tcod.event.KeySym.SLASH:
            return LookHandler(self.engine)
        if key == tcod.event.KeySym.H:
            return KeybindScreen(self)

        c_event = get_event_by_id(9)
        if key == tcod.event.KeySym(c_event["KEY"]) and modifier == tcod.event.Modifier(
            c_event["MOD"]
        ):
            return EquipmentScreen(self.engine)

        if key == tcod.event.KeySym.F1 and CHEATS:
            return CheatActiveHandler(self.engine)
        elif key == tcod.event.KeySym.F2 and CHEATS:
            return EnemyCheatActiveHandler(self.engine)
        elif key == tcod.event.KeySym.F3 and CHEATS:
            return GerneralCheatActiveHandler(self.engine)
        elif key == tcod.event.KeySym.F4 and CHEATS:
            return GerneralCheatActivationActiveHandler(self.engine)
        elif key == tcod.event.KeySym.F5 and CHEATS:
            return AffixCheatActiveHandler(self.engine)
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

    def on_render(self, console: tcod.Console) -> None:
        super().on_render(console)
        log_console = tcod.console.Console(console.width - 6, console.height - 6)
        log_console.print(
            x=0,
            y=0,
            width=log_console.width,
            height=1,
            text="|Message history|",
            alignment=libtcodpy.CENTER,
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


class EquipmentScreen(AskUserEventHandler):
    TITLE = "Equipments"

    def on_render(self, console):
        super().on_render(console)
        x = 0
        y = 0
        width = len(self.TITLE) + 40

        console.draw_frame(
            x=x,
            y=y,
            width=width,
            height=40,
            title=self.TITLE,
            clear=True,
            fg=(255, 255, 255),
            bg=(0, 0, 0),
        )
        # this increment is for not writin in title line
        y += 1
        for equip in self.engine.player.equipment.__dict__:
            if "_" not in equip and "parent" not in equip:
                slot = getattr(self.engine.player.equipment, equip)
                console.print(x=x + 1, y=y, string=f"{equip.capitalize():<11}:")
                if slot:
                    line = slot.name
                    x_save = x
                    if slot.equippable.defense_bonus != 0:
                        line = line + f" Defense: {slot.equippable.defense_bonus}"
                    if slot.equippable.power_bonus != 0:
                        line = line + f" Attack: {slot.equippable.power_bonus}"
                    console.print(x=x + 13, y=y, string=line)
                    x += 13
                    x = x_save

                y += 2


class ItemCheatScreen(AskUserEventHandler):
    TITLE = "Item cheats"

    def on_render(self, console):
        super().on_render(console)
        x = 0
        y = 0
        title = f"{self.TITLE} Floor {self.engine.current_cheat_page}"
        width = len(title) + 15
        pages = []
        for floor in self.engine.item_chances:
            pages.append(floor)

        console.draw_frame(
            x=x,
            y=y,
            width=width,
            height=40,
            title=title,
            clear=True,
            fg=(255, 255, 255),
            bg=(0, 0, 0),
        )
        # this increment is for not writin in title line
        y += 1
        if self.engine.current_cheat_page > len(self.engine.item_chances) - 1:
            # set to 0 so that different indecies from different cheat menues dont wrongfully collide
            self.engine.current_cheat_page = 0
        itemOnFloor = self.engine.item_chances[self.engine.current_cheat_page]
        for i, item in enumerate(itemOnFloor):
            item_key = chr(ord("a") + i)
            item_string = f"({item_key}) {item[0].name}"
            console.print(x + 1, y + i + 1, item_string)

    def ev_keydown(self, event) -> Optional[ActionOrHandler]:
        key = event.sym
        index = key - tcod.event.KeySym.A

        if not cheatNav(engine=self.engine, key=key, arr=self.engine.item_chances):
            if 0 <= index <= 26:
                try:
                    selected_item = self.engine.item_chances[
                        self.engine.current_cheat_page
                    ][index]
                except IndexError:
                    self.engine.message_log.add_message(
                        "Invalid input slot.", color.invalid
                    )
                    return None
                return self.on_item_selected(selected_item)
        return super().ev_keydown(event)


class CheatActiveHandler(ItemCheatScreen):
    def on_item_selected(self, item: Item) -> Optional[ActionOrHandler]:
        item[0].spawn(
            gamemap=self.engine.game_map, x=self.engine.player.x, y=self.engine.player.y
        )
        self.engine.message_log.add_message(f"The Tower creates 1 {item[0].name}")


class EnemyCheatScreen(AskUserEventHandler):
    TITLE = "Enemy cheats"

    def on_render(self, console):
        super().on_render(console)
        x = 0
        y = 0
        title = f"{self.TITLE} Floor {self.engine.current_cheat_page}"
        width = len(title) + 15
        pages = []
        for floor in self.engine.enemy_chances:
            pages.append(floor)

        console.draw_frame(
            x=x,
            y=y,
            width=width,
            height=40,
            title=title,
            clear=True,
            fg=(255, 255, 255),
            bg=(0, 0, 0),
        )
        # this increment is for not writin in title line
        y += 1
        if self.engine.current_cheat_page > len(self.engine.enemy_chances) - 1:
            self.engine.current_cheat_page = 0
        enemyOnFloor = self.engine.enemy_chances[self.engine.current_cheat_page]
        for i, enemy in enumerate(enemyOnFloor):
            enemyKey = chr(ord("a") + i)
            enemyString = f"({enemyKey}) {enemy[0].name}"
            console.print(x + 1, y + i + 1, enemyString)

    def ev_keydown(self, event) -> Optional[ActionOrHandler]:
        key = event.sym
        index = key - tcod.event.KeySym.A

        if not cheatNav(engine=self.engine, key=key, arr=self.engine.enemy_chances):
            if 0 <= index <= 26:
                try:
                    selected_enemy = self.engine.enemy_chances[
                        self.engine.current_cheat_page
                    ][index]
                except IndexError:
                    self.engine.message_log.add_message(
                        "Invalid input slot.", color.invalid
                    )
                    return None
                return self.on_enemy_selected(selected_enemy)
        return super().ev_keydown(event)


class EnemyCheatActiveHandler(EnemyCheatScreen):
    def on_enemy_selected(self, enemy: Actor) -> Optional[ActionOrHandler]:
        enemy[0].spawn(
            gamemap=self.engine.game_map,
            x=self.engine.player.x + 1,
            y=self.engine.player.y,
        )
        self.engine.message_log.add_message(f"The Tower creates 1 {enemy[0].name}")


# Since it was now reused code this is now its own function
# Cheat Navigation is now reusable
def cheatNav(key, engine, arr) -> bool:
    if key == tcod.event.KeySym.PAGEUP:
        if len(arr) - 1 >= engine.current_cheat_page + 1:
            engine.current_cheat_page += 1
        else:
            engine.current_cheat_page = 0
            return True
    elif key == tcod.event.KeySym.PAGEDOWN:
        if 0 <= engine.current_cheat_page - 1:
            engine.current_cheat_page -= 1
        else:
            engine.current_cheat_page = len(arr) - 1
            return True
    return False


class GeneralCheats(AskUserEventHandler):
    TITLE = "Gerneral Cheats"

    def on_render(self, console):
        super().on_render(console)
        x = 0
        y = 0
        title = f"{self.TITLE}"
        width = len(title) + 15

        console.draw_frame(
            x=x,
            y=y,
            width=width,
            height=40,
            title=title,
            clear=True,
            fg=(255, 255, 255),
            bg=(0, 0, 0),
        )
        # this increment is for not writin in title line
        y += 1
        for i, cheat in enumerate(GENERAL_CHEATS):
            cheatKey = chr(ord("a") + i)
            cheatString = f"({cheatKey}) {cheat:<17}: {GENERAL_CHEATS[cheat]}"
            console.print(x + 1, y + i + 1, cheatString)

    def ev_keydown(self, event) -> Optional[ActionOrHandler]:
        key = event.sym
        index = key - tcod.event.KeySym.A

        if 0 <= index <= 26:
            try:
                cheatSelected = list(GENERAL_CHEATS)[index]
            except IndexError:
                self.engine.message_log.add_message(
                    "Invalid input slot.", color.invalid
                )
                return None
            return self.on_cheat_select(cheatSelected)
        return super().ev_keydown(event)


class GerneralCheatActiveHandler(GeneralCheats):
    def on_cheat_select(self, cheat) -> Optional[ActionOrHandler]:
        if GENERAL_CHEATS[cheat]:
            GENERAL_CHEATS[cheat] = False
        else:
            GENERAL_CHEATS[cheat] = True


class GeneralCheatsActivaions(AskUserEventHandler):
    TITLE = "Gerneral Cheats to Activate"

    def on_render(self, console):
        super().on_render(console)
        x = 0
        y = 0
        title = f"{self.TITLE}"
        width = len(title) + 15

        console.draw_frame(
            x=x,
            y=y,
            width=width,
            height=40,
            title=title,
            clear=True,
            fg=(255, 255, 255),
            bg=(0, 0, 0),
        )
        # this increment is for not writin in title line
        y += 1
        for i, cheat in enumerate(GENERAL_CHEAT_ACTIVATIONS):
            cheatKey = chr(ord("a") + i)
            cheatString = f"({cheatKey}) {cheat:<17}"
            console.print(x + 1, y + i + 1, cheatString)

    def ev_keydown(self, event) -> Optional[ActionOrHandler]:
        key = event.sym
        index = key - tcod.event.KeySym.A

        if 0 <= index <= 26:
            try:
                cheatSelected = list(GENERAL_CHEAT_ACTIVATIONS)[index]
            except IndexError:
                self.engine.message_log.add_message(
                    "Invalid input slot.", color.invalid
                )
                return None
            return self.on_cheat_select(cheatSelected)
        return super().ev_keydown(event)


class GerneralCheatActivationActiveHandler(GeneralCheatsActivaions):
    def on_cheat_select(self, cheat) -> Optional[ActionOrHandler]:
        from procgen import generate_shop_room

        match cheat:
            case "spawn_shop":
                self.engine.game_map = generate_shop_room(
                    engine=self.engine,
                    map_width=100,
                    map_height=100,
                    current_floor=self.engine.game_world.current_floor,
                )
            case "current_floor_+":
                self.engine.game_world.current_floor += 1
            case "current_floor_-":
                self.engine.game_world.current_floor -= 1
            case "level_up":
                self.engine.player.level.current_xp = (
                    self.engine.player.level.xp_to_next_level
                )
                return LevelUpEventHandler(engine=self.engine)
            case "die":
                self.engine.player.fighter.die()


class AffixCheatScreen(AskUserEventHandler):
    TITLE = "Affix cheats"

    def on_render(self, console):
        if self.engine.current_cheat_page > len(self.engine.enemy_chances) - 1:
            self.engine.current_cheat_page = 0
        affixesOnPage = array_split(
            self.engine.affixManager.get_affix_dir(),
            math.ceil(len(self.engine.affixManager.get_affix_dir()) / 25),
        )[self.engine.current_cheat_page]

        super().on_render(console)
        x = 0
        y = 0
        title = f"{self.TITLE} Page {self.engine.current_cheat_page}"
        width = len(title) + 25
        pages = []
        for floor in self.engine.enemy_chances:
            pages.append(floor)

        console.draw_frame(
            x=x,
            y=y,
            width=width,
            height=3 + len(affixesOnPage),
            title=title,
            clear=True,
            fg=(255, 255, 255),
            bg=(0, 0, 0),
        )
        # this increment is for not writin in title line
        y += 1
        for i, affix_page in enumerate(affixesOnPage):
            affix_key = chr(ord("a") + i)
            affixString = f"({affix_key}) {affix_page.AFFIX_NAME}"
            console.print(
                x + 1, y + i + 1, text=affixString, fg=affix_page.AFFIX_COLOR.value
            )

    def ev_keydown(self, event) -> Optional[ActionOrHandler]:
        key = event.sym
        index = key - tcod.event.KeySym.A
        affixesPages = array_split(
            self.engine.affixManager.get_affix_dir(),
            math.ceil(len(self.engine.affixManager.get_affix_dir()) / 25),
        )
        affixesOnPage = array_split(
            self.engine.affixManager.get_affix_dir(),
            math.ceil(len(self.engine.affixManager.get_affix_dir()) / 25),
        )[self.engine.current_cheat_page]

        if not cheatNav(engine=self.engine, key=key, arr=affixesPages):
            if 0 <= index <= 26:
                try:
                    affix_selected = affixesOnPage[index]
                except IndexError:
                    self.engine.message_log.add_message(
                        "Invalid input slot.", color.invalid
                    )
                    return None
                return self.on_affix_selected(affix_selected)
        return super().ev_keydown(event)


class AffixCheatActiveHandler(AffixCheatScreen):
    def on_affix_selected(self, affix: affix.Affix) -> Optional[ActionOrHandler]:
        self.engine.affixManager.gain_affix(affix)
        self.engine.message_log.add_message(f"The Tower grants you {affix.AFFIX_NAME}")



# class LevelEditorHandler(BaseEventHandler):
#     def __init__(
#             self, parent_handler: BaseEventHandler
#         ):
#             self.parent = parent_handler
#             self.mouse_location = (0, 0)
#             self.console = []

#     def on_render(self, console : tcod.console.Console):
#         console.print
        

#     def ev_keydown(self, event):
#         #TODO Impl inputs for user and stuff
#         key = event.sym
#         if key == tcod.event.KeySym.ESCAPE:
#             return self.parent
#         elif key == tcod.event.KeySym.SPACE:
#             self.console.print(1, 1, "Test")
#             self.on_render(self.console)
#             return self
        

#     def ev_mousemotion(self, event: tcod.event.MouseMotion) -> None:
#         self.mouse_location = int(event.tile.x), int(event.tile.y)
import re
NAME_MAX_LENGTH = 24
VIEW_WIDTH = 60
VIEW_HEIGHT = 50
PANEL_X = VIEW_WIDTH
PANEL_WIDTH = 20
PANEL_HIGHLIGHT = (90, 20, 20)
PALETTE_ROWS = 16
SHIFT = tcod.event.Modifier.LSHIFT | tcod.event.Modifier.RSHIFT
CTRL = tcod.event.Modifier.LCTRL | tcod.event.Modifier.RCTRL
NAME_PATTERN = re.compile(r"^[A-Za-z0-9 _\-]+$")


class TextPrompt(BaseEventHandler):
    def __init__(
        self,
        parent: BaseEventHandler,
        title: str,
        text: str,
        on_submit: Callable[[str], Optional[BaseEventHandler]],
    ):
        self.parent = parent
        self.title = title
        self.text = text
        self.on_submit = on_submit
        self.error = ""

    def on_render(self, console):
        self.parent.on_render(console)
        dim(console)
        width = NAME_MAX_LENGTH + 8
        x, y = draw_box(console, width, 7, self.title)
        console.print(x + 2, y + 2, (self.text + "_").ljust(NAME_MAX_LENGTH + 1),
                      fg=color.menu_title, bg=(40, 10, 10))
        console.print(x + 2, y + 4, "[Enter] ok  [Esc] cancel", fg=color.impossible)
        if self.error:
            console.print(x + 2, y + 5, self.error[: width - 4], fg=color.error)

    def ev_keydown(self, event):
        key = event.sym
        if key == tcod.event.KeySym.ESCAPE:
            return self.parent
        if key in CONFIRM_KEYS:
            return self.on_submit(self.text.strip())
        if key == tcod.event.KeySym.BACKSPACE:
            self.text = self.text[:-1]
            self.error = ""
            return None
        char = key_to_char(event)
        if char and len(self.text) < NAME_MAX_LENGTH:
            self.text += char
            self.error = ""
        return None

class PopupToConfirm(BaseEventHandler):
    def __init__(
        self,
        parent: BaseEventHandler,
        text: str,
        on_yes: Callable[[], BaseEventHandler],
    ):
        self.parent = parent
        self.text = text
        self.on_yes = on_yes

    def on_render(self, console):
        self.parent.on_render(console)
        dim(console)
        width = max(len(self.text), 20) + 4
        x, y = draw_box(console, width, 5, "Sure?")
        console.print(x + 2, y + 1, self.text)
        console.print(x + 2, y + 3, "[Y] yes  [N] no", fg=color.impossible)

    def ev_keydown(self, event):
        if event.sym == tcod.event.KeySym.Y:
            return self.on_yes()
        if event.sym in (tcod.event.KeySym.N, tcod.event.KeySym.ESCAPE):
            return self.parent
        return None


def draw_box(console, width:int, height: int, title:str) -> Tuple[int,int]:
    x = (console.width - width) // 2
    y = (console.height - height) // 2
    console.draw_frame(
        x=x, y=y, width=width, height = height, title = title, clear = True, fg=color.white, bg=color.black
    )
    return x,y

def dim(console: tcod.console.Console) ->None:
    console.rgb["fg"] //= 4
    console.rgb["bg"] //= 4


def key_to_char(event) -> Optional[str]:
    sym = int(event.sym)
    shifted = bool(event.mod & SHIFT)
    if ord("a") <= sym <= ord("z"):
        char = chr(sym)
        return char.upper() if shifted else char
    if ord("0") <= sym <= ord("9") and not shifted:
        return chr(sym)
    if sym == int(tcod.event.KeySym.SPACE):
        return " "
    if sym == int(tcod.event.KeySym.MINUS):
        return "_" if shifted else "-"
    return None

# what Shift turns each key into on a US keyboard
US_SHIFTED = {
    "1": "!", "2": "@", "3": "#", "4": "$", "5": "%", "6": "^", "7": "&",
    "8": "*", "9": "(", "0": ")", "-": "_", "=": "+", "[": "{", "]": "}",
    "\\": "|", ";": ":", "'": '"', ",": "<", ".": ">", "/": "?", "`": "~",
}


def typed_char(event) -> Optional[str]:
    """Any printable character for a US keyboard layout, punctuation included."""
    sym = int(event.sym)
    if not 32 <= sym < 127:
        return None
    char = chr(sym)
    shifted = bool(event.mod & SHIFT)
    if char == " ":
        return char
    if "a" <= char <= "z":
        caps = bool(event.mod & tcod.event.Modifier.CAPS)
        return char.upper() if shifted != caps else char
    if char in US_SHIFTED:
        return US_SHIFTED[char] if shifted else char
    return None


def check_name(name: str) -> str:
    if not name:
        return "The level needs a name"
    if not NAME_PATTERN.match(name):
        return "Use letters, numbers, space, - and _"
    return ""

class ChoicePopup(BaseEventHandler):

    def __init__(self, parent, title, options):
        self.parent = parent
        self.title = title
        self.options = options

    def on_render(self, console):
        self.parent.on_render(console)
        dim(console)
        width = max(len(self.title), *(len(label) + 4 for _, label, _ in self.options)) + 4
        x, y = draw_box(console, width, len(self.options) + 4, self.title)
        for i, (key, label, _) in enumerate(self.options):
            console.print(x + 2, y + 2 + i, f"[{chr(key).upper()}] {label}")

    def ev_keydown(self, event):
        if event.sym == tcod.event.KeySym.ESCAPE:
            return self.parent
        for key, _, callback in self.options:
            if event.sym == key:
                return callback()
        return None

class CampaignVictoryHandler(BaseEventHandler):
    def __init__(self, engine: Engine):
        self.engine = engine
        # the run is over: record it like a death does, and drop the save
        engine.scoreboard.add_score(engine.player.level.xp_given)
        engine.scoreboard.save()
        if os.path.exists("savegame.sav"):
            os.remove("savegame.sav")

    def on_render(self, console):
        self.engine.render(console)
        dim(console)
        campaign = self.engine.game_world.campaign
        name = campaign.name if campaign else "the campaign"
        lines = [
            f"{name} is conquered.",
            "",
            f"Floors climbed: {self.engine.game_world.current_floor + 1}",
            f"Level: {self.engine.player.level.current_level}",
            "",
            "[Enter] return to the main menu",
        ]
        width = max(len(line) for line in lines) + 6
        x, y = draw_box(console, width, len(lines) + 4, "The flesh yields")
        for i, line in enumerate(lines):
            console.print(x + 3, y + 2 + i, line, fg=color.menu_title if i == 0 else color.menu_text)

    def ev_keydown(self, event):
        if event.sym in CONFIRM_KEYS or event.sym == tcod.event.KeySym.ESCAPE:
            from setup_game import MainMenu

            return MainMenu()
        return None

# Dialogue lives beneathe here

class ListPicker(BaseEventHandler):

    def __init__(self, parent, title, items, on_pick):
        self.parent = parent
        self.title = title
        self.items = items
        self.on_pick = on_pick
        self.selected = 0

    def on_render(self, console):
        self.parent.on_render(console)
        dim(console)
        width = max([len(self.title) + 4] + [len(d) + 6 for d, _ in self.items]) + 4
        x, y = draw_box(console, width, len(self.items) + 4, self.title)
        if not self.items:
            console.print(x + 2, y + 1, "Nothing here", fg=color.impossible)
        for i, (display, _) in enumerate(self.items):
            text = f" {display}".ljust(width - 4)
            if i == self.selected:
                console.print(x + 2, y + 2 + i, text, fg=color.menu_title, bg=(90, 20, 20))
            else:
                console.print(x + 2, y + 2 + i, text)

    def ev_keydown(self, event):
        key = event.sym
        if key == tcod.event.KeySym.ESCAPE:
            return self.parent
        if not self.items:
            return None
        if key == tcod.event.KeySym.UP:
            self.selected = (self.selected - 1) % len(self.items)
        elif key == tcod.event.KeySym.DOWN:
            self.selected = (self.selected + 1) % len(self.items)
        elif key in CONFIRM_KEYS:
            return self.on_pick(self.items[self.selected][1])
        return None

class PropertyMenu(BaseEventHandler):
    def __init__(self, editor, pos, fields):
        self.editor = editor  # the LevelEditor, also the screen we return to
        self.pos = pos
        self.fields = fields  # [(key, kind)]
        self.selected = 0

    @property
    def values(self):
        return self.editor.level.properties.setdefault(self.pos, {})

    def set_value(self, key, value):
        self.values[key] = value
        self.editor.dirty = True
        return self

    def on_render(self, console):
        self.editor.on_render(console)
        dim(console)
        width = 44
        x, y = draw_box(console, width, len(self.fields) + 5, "Properties")
        for i, (key, kind) in enumerate(self.fields):
            value = self.values.get(key, "-")
            text = f" {key}: {value}"[: width - 4].ljust(width - 4)
            bg = (90, 20, 20) if i == self.selected else color.black
            console.print(x + 2, y + 2 + i, text, bg=bg)
        console.print(x + 2, y + len(self.fields) + 3, "[Enter] edit  [Esc] done", fg=color.impossible)

    def ev_keydown(self, event):
        key = event.sym
        if key == tcod.event.KeySym.ESCAPE:
            return self.editor
        if key == tcod.event.KeySym.UP:
            self.selected = (self.selected - 1) % len(self.fields)
        elif key == tcod.event.KeySym.DOWN:
            self.selected = (self.selected + 1) % len(self.fields)
        elif key in CONFIRM_KEYS:
            return self.edit(*self.fields[self.selected])
        return None

    def edit(self, key, kind):
        if kind == "text":
            return TextPrompt(self, key, self.values.get(key, ""),
                              lambda text: self.set_value(key, text))
        if kind == "dialogue":
            from components.dialouge_parser import list_dialogues, load_dialogue
            from components.settings import DIALOGUE_DIR

            def pick(filename):
                try:  # check the file now, not when a player talks to the NPC
                    load_dialogue(os.path.join(DIALOGUE_DIR, filename))
                except Exception as exc:
                    return PopupMessage(self, f"Broken dialogue:\n{exc}",
                                        halved=True, alignment=libtcodpy.CENTER)
                return self.set_value(key, filename)

            return ListPicker(self, "Choose dialogue", list_dialogues(), pick)
        if kind == "lore":
            from components.settings import LORE_DIR
            from components.dialouge_parser import list_lore
            from level_editor import find_lore_users

            def open_editor(filename, text):
                others = find_lore_users(filename, self.editor.level, self.pos)
                title = filename + (f" (used {len(others)}x more)" if others else "")

                def save(new_text):
                    os.makedirs(LORE_DIR, exist_ok=True)
                    with open(os.path.join(LORE_DIR, filename), "w", encoding="utf-8") as f:
                        f.write(new_text)
                    return self.set_value(key, filename)

                return LoreEditor(self, title, text, save)

            def new_text():
                def submit(name):
                    if not name:
                        prompt.error = "The text needs a name"
                        return None
                    problem = check_name(name)
                    if problem:
                        prompt.error = problem
                        return None
                    filename = name.replace(" ", "_") + ".txt"
                    if os.path.exists(os.path.join(LORE_DIR, filename)):
                        prompt.error = f"{name} already exists"
                        return None
                    return open_editor(filename, "")  # file is written on save only

                prompt = TextPrompt(self, "Name of the new text", "", submit)
                return prompt

            def pick(filename):
                if filename is None:
                    return new_text()

                def choose(choice):
                    if choice == "use":
                        return self.set_value(key, filename)
                    try:
                        with open(os.path.join(LORE_DIR, filename), encoding="utf-8") as f:
                            text = f.read()
                    except OSError as exc:
                        return PopupMessage(self, f"Can't read {filename}:\n{exc}",
                                            halved=True, alignment=libtcodpy.CENTER)
                    return open_editor(filename, text)

                return ListPicker(self, filename, [("Use this", "use"), ("Edit", "edit")], choose)

            return ListPicker(self, "Choose text", [("+ New text...", None)] + list_lore(), pick)
        if kind == "quest_id":
            def submit(text):
                if not text:
                    self.values.pop(key, None)
                    self.editor.dirty = True
                    return self
                from components.dialouge_parser import quest_key
                from level_editor import find_quest_id

                quest_id = quest_key(text)
                self.set_value(key, quest_id)
                produced, used = find_quest_id(quest_id, self.editor.level, self.pos)
                if not produced and not used:
                    return self
                lines = [f"ID '{quest_id}'"]
                if produced:
                    lines += ["", "Also produced by:"] + produced
                if used:
                    lines += ["", "Used by:"] + used
                return PopupMessage(self, "\n".join(lines), halved=True,
                                    alignment=libtcodpy.CENTER)

            return TextPrompt(self, key, self.values.get(key, ""), submit)
        if kind == "bool":
            from level_editor import is_yes

            return self.set_value(key, "no" if is_yes(self.values.get(key)) else "yes")
        if kind == "link_id":
            def submit(text):
                if not text:
                    self.values.pop(key, None)
                    self.editor.dirty = True
                    return self
                from components.dialouge_parser import quest_key
                from level_editor import find_link_id, TILE_NAMES

                link_id = quest_key(text)
                self.set_value(key, link_id)
                me = TILE_NAMES[int(self.editor.level.tiles[self.pos])]
                others = find_link_id(self.editor.level, link_id, self.pos)
                lines = [f"ID '{link_id}'", ""]
                if others:
                    lines.append("Already used by:")
                    lines += [f"{kind_} at {x},{y}" for kind_, (x, y) in others]
                else:
                    lines.append("Not linked yet")
                counterpart = "Door" if me == "Button" else "Button"
                if not any(kind_ == counterpart for kind_, _ in others):
                    lines += ["", f"No {counterpart.lower()} uses this id yet"]
                return PopupMessage(self, "\n".join(lines), halved=True,
                                    alignment=libtcodpy.CENTER)

            return TextPrompt(self, key, self.values.get(key, ""), submit)
        return None

class LoreEditor(BaseEventHandler):
    """Multi-line text editor for lore files, used from the level editor."""

    WIDTH = 56  # same box as ReadingScreen, so lines wrap like they will in game
    ROWS = 30
    CURSOR_BG = (150, 40, 40)

    def __init__(self, parent, title, text, on_save):
        self.parent = parent
        self.title = title
        self.on_save = on_save  # (text) -> handler, writes the file
        self.lines = text.split("\n") if text else [""]
        self.row = 0
        self.col = 0
        self.scroll = 0
        self.dirty = False
        self.error = ""

    def segments(self):
        """Screen rows as (line, start, end), each line wrapped at spaces."""
        width = self.WIDTH - 4
        result = []
        for row, line in enumerate(self.lines):
            start = 0
            while len(line) - start > width:
                space = line.rfind(" ", start + 1, start + width + 1)
                end = space + 1 if space > start else start + width
                result.append((row, start, end))
                start = end
            result.append((row, start, len(line)))
        return result

    def cursor_segment(self, segments) -> int:
        for i, (row, start, end) in enumerate(segments):
            if row == self.row and start <= self.col and (
                self.col < end or end == len(self.lines[row])
            ):
                return i
        return 0

    def move_vertical(self, step: int) -> None:
        segments = self.segments()
        i = self.cursor_segment(segments)
        x = self.col - segments[i][1]
        j = max(0, min(i + step, len(segments) - 1))
        row, start, end = segments[j]
        last = j + 1 == len(segments) or segments[j + 1][0] != row
        self.row = row
        self.col = min(start + x, end if last else max(start, end - 1))

    def insert(self, text: str) -> None:
        line = self.lines[self.row]
        self.lines[self.row] = line[: self.col] + text + line[self.col :]
        self.col += len(text)
        self.dirty = True

    def newline(self) -> None:
        line = self.lines[self.row]
        self.lines[self.row] = line[: self.col]
        self.lines.insert(self.row + 1, line[self.col :])
        self.row += 1
        self.col = 0
        self.dirty = True

    def backspace(self) -> None:
        if self.col > 0:
            line = self.lines[self.row]
            self.lines[self.row] = line[: self.col - 1] + line[self.col :]
            self.col -= 1
        elif self.row > 0:
            self.col = len(self.lines[self.row - 1])
            self.lines[self.row - 1] += self.lines.pop(self.row)
            self.row -= 1
        else:
            return
        self.dirty = True

    def delete(self) -> None:
        line = self.lines[self.row]
        if self.col < len(line):
            self.lines[self.row] = line[: self.col] + line[self.col + 1 :]
        elif self.row + 1 < len(self.lines):
            self.lines[self.row] += self.lines.pop(self.row + 1)
        else:
            return
        self.dirty = True

    def save(self):
        try:
            handler = self.on_save("\n".join(self.lines))
        except OSError as exc:
            self.error = f"Save failed: {exc}"
            return None
        self.dirty = False
        return handler

    def leave(self):
        if self.dirty:
            return PopupToConfirm(self, "Discard changes?", lambda: self.parent)
        return self.parent

    def on_render(self, console):
        self.parent.on_render(console)
        dim(console)
        segments = self.segments()
        cursor = self.cursor_segment(segments)
        if cursor < self.scroll:
            self.scroll = cursor
        elif cursor >= self.scroll + self.ROWS:
            self.scroll = cursor - self.ROWS + 1

        title = self.title + ("*" if self.dirty else "")
        x, y = draw_box(console, self.WIDTH, self.ROWS + 5, title)
        for i, (row, start, end) in enumerate(segments[self.scroll : self.scroll + self.ROWS]):
            console.print(x + 2, y + 2 + i, self.lines[row][start:end])

        line = self.lines[self.row]
        char = line[self.col] if self.col < len(line) else " "
        cx = x + 2 + self.col - segments[cursor][1]
        cy = y + 2 + cursor - self.scroll
        console.print(cx, cy, char, bg=self.CURSOR_BG)

        if self.error:
            console.print(x + 2, y + self.ROWS + 3, self.error[: self.WIDTH - 4], fg=color.error)
        else:
            console.print(x + 2, y + self.ROWS + 3, "[Ctrl+S] save  [Esc] back", fg=color.impossible)

    def ev_keydown(self, event):
        key = event.sym
        k = tcod.event.KeySym
        self.error = ""
        if event.mod & CTRL:
            if key == k.S:
                return self.save()
            return None
        if key == k.ESCAPE:
            return self.leave()
        if key in CONFIRM_KEYS:
            self.newline()
        elif key == k.BACKSPACE:
            self.backspace()
        elif key == k.DELETE:
            self.delete()
        elif key == k.LEFT:
            if self.col > 0:
                self.col -= 1
            elif self.row > 0:
                self.row -= 1
                self.col = len(self.lines[self.row])
        elif key == k.RIGHT:
            if self.col < len(self.lines[self.row]):
                self.col += 1
            elif self.row + 1 < len(self.lines):
                self.row += 1
                self.col = 0
        elif key == k.UP:
            self.move_vertical(-1)
        elif key == k.DOWN:
            self.move_vertical(1)
        elif key == k.PAGEUP:
            self.move_vertical(-self.ROWS)
        elif key == k.PAGEDOWN:
            self.move_vertical(self.ROWS)
        elif key == k.HOME:
            self.col = 0
        elif key == k.END:
            self.col = len(self.lines[self.row])
        else:
            char = typed_char(event)
            if char:
                self.insert(char)
        return None


def wrap_text(text: str, width: int) -> list:
    lines = []
    for paragraph in text.splitlines():
        lines.extend(textwrap.wrap(paragraph, width) or [""])
    return lines

def tag_values(passage, prefix: str) -> list:
    return [quest_key(tag[len(prefix):]) for tag in passage.tags if tag.startswith(prefix)]


def find_quest_item(player, quest_id: str):
    for item in player.inventory.items:
        if getattr(item, "quest_id", None) == quest_id:
            return item
    return None


def give_item(engine, item) -> None:
    """Puts an item into the player's inventory, or on the floor if it is full."""
    player = engine.player
    if len(player.inventory.items) < player.inventory.capacity:
        item.parent = player.inventory
        player.inventory.items.append(item)
        engine.message_log.add_message(f"You receive the {item.name}.", color.menu_title)
    else:
        item.place(player.x, player.y, engine.game_map)
        engine.message_log.add_message(
            f"Your hands are full. The {item.name} falls to the floor.", color.menu_title
        )


def give_quest_item(engine, quest_id: str) -> None:
    import entity_factory

    item = copy.deepcopy(entity_factory.quest_item)
    item.quest_id = quest_id
    item.name = quest_id.replace("_", " ").title()
    give_item(engine, item)

class DialogueScreen(AskUserEventHandler):
    WIDTH = 50

    def __init__(self, engine, npc):
        super().__init__(engine)
        self.npc = npc
        self.dialogue = npc.dialogue
        # passages whose gives/takes already ran for this NPC
        if not hasattr(npc, "dialogue_done"):
            npc.dialogue_done = set()
        self.enter(self.dialogue.start)

    def can_enter(self, name: str) -> bool:
        target = self.dialogue.passages[name]
        player = self.engine.player
        return all(find_quest_item(player, q) for q in tag_values(target, "requires:"))

    def enter(self, name: str) -> None:
        import entity_factory
        from entity import Item

        self.current = name
        passage = self.passage
        if name in self.npc.dialogue_done:
            return

        player = self.engine.player
        log = self.engine.message_log
        changed = False  # anything handed over: then this passage only runs once

        for quest_id in tag_values(passage, "takes:"):
            item = find_quest_item(player, quest_id)
            if item is not None:
                player.inventory.items.remove(item)
                log.add_message(f"You hand over the {item.name}.")
                changed = True

        for quest_id in tag_values(passage, "gives:"):
            give_quest_item(self.engine, quest_id)
            changed = True

        for attr in tag_values(passage, "item:"):
            prototype = getattr(entity_factory, attr, None)
            if not isinstance(prototype, Item):
                print(f"Dialogue tag item:{attr} names no item in entity_factory")
                continue
            give_item(self.engine, copy.deepcopy(prototype))
            changed = True

        for amount in tag_values(passage, "organs:"):
            try:
                organs = int(amount)
            except ValueError:
                print(f"Dialogue tag organs:{amount} is not a number")
                continue
            player.currency += organs
            if organs >= 0:
                log.add_message(f"You receive {organs} organs.", color.menu_title)
            else:
                log.add_message(f"You pay {-organs} organs.")
            changed = True

        if changed:
            self.npc.dialogue_done.add(name)

    def answers(self):
        """The answers the player may pick. Links into passages whose
        requirements are not met are hidden."""
        links = [(label, target) for label, target in self.passage.links if self.can_enter(target)]
        return links or [("Leave", None)]
    
    @property
    def passage(self):
        return self.dialogue.passages[self.current]

    def on_render(self, console):
        super().on_render(console)
        dim(console)
        inner = self.WIDTH - 4
        text_lines = wrap_text(self.passage.text, inner)
        answer_lines = [
            wrap_text(f"{i + 1}) {label}", inner) for i, (label, _) in enumerate(self.answers())
        ]
        height = len(text_lines) + sum(len(lines) for lines in answer_lines) + 5
        x, y = draw_box(console, self.WIDTH, height, self.npc.name)

        row = y + 2
        for line in text_lines:
            console.print(x + 2, row, line)
            row += 1
        row += 1
        for lines in answer_lines:
            for line in lines:
                console.print(x + 2, row, line, fg=color.menu_title)
                row += 1

    def ev_keydown(self, event):
        key = event.sym
        k = tcod.event.KeySym
        if key == k.ESCAPE:
            return MainGameEventHandler(self.engine)

        if k.N1 <= key <= k.N9:
            index = key - k.N1
        elif k.KP_1 <= key <= k.KP_9:
            index = key - k.KP_1
        elif key in CONFIRM_KEYS and not self.passage.links:
            index = 0  # Enter also closes a finished conversation
        else:
            return None

        answers = self.answers()
        if index >= len(answers):
            return None
        label, target = answers[index]
        if target is None:
            return MainGameEventHandler(self.engine)
        self.enter(target)
        return None

    def ev_mousebuttondown(self, event):
        return None  # don't close the conversation on a stray click

class ReadingScreen(AskUserEventHandler):
    WIDTH = 56
    MAX_ROWS = 30  # text rows visible at once, longer texts scroll

    def __init__(self, engine, item):
        super().__init__(engine)
        self.item = item
        self.lines = wrap_text(item.lore, self.WIDTH - 4)
        self.scroll = 0

    @property
    def rows(self):
        return min(len(self.lines), self.MAX_ROWS)

    def on_render(self, console):
        super().on_render(console)
        dim(console)
        x, y = draw_box(console, self.WIDTH, self.rows + 5, self.item.name)
        for i, line in enumerate(self.lines[self.scroll : self.scroll + self.rows]):
            console.print(x + 2, y + 2 + i, line)

        hint = "[Esc] close"
        if len(self.lines) > self.rows:
            hint = "Up/Down scroll  " + hint
        console.print(x + 2, y + self.rows + 3, hint, fg=color.impossible)

    def ev_keydown(self, event):
        key = event.sym
        k = tcod.event.KeySym
        last = max(0, len(self.lines) - self.rows)
        if key == k.UP:
            self.scroll = max(0, self.scroll - 1)
        elif key == k.DOWN:
            self.scroll = min(last, self.scroll + 1)
        elif key == k.PAGEUP:
            self.scroll = max(0, self.scroll - self.rows)
        elif key == k.PAGEDOWN:
            self.scroll = min(last, self.scroll + self.rows)
        elif key == k.ESCAPE or key in CONFIRM_KEYS:
            return MainGameEventHandler(self.engine)
        return None

    def ev_mousebuttondown(self, event):
        return None