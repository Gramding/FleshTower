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
from components.dialouge_parser import quest_key


from components.settings import (
    CHEATS,
    GENERAL_CHEATS,
    GENERAL_CHEAT_ACTIVATIONS,
    PlayerClass,
)
import components.affix as affix
from components import stats

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
    # diagonals (Y U B N), only with stats.PLAYER_DIAGONALS
    104: (-1, -1),
    105: (1, -1),
    106: (-1, 1),
    107: (1, 1),
}
DIAGONAL_MOVES = (104, 105, 106, 107)

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
            return resume_game(self.engine)
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
        self.engine.player.fighter.regenerate()
        game_map = self.engine.game_map
        in_combat = any(
            actor.ai and actor is not self.engine.player and game_map.visible[actor.x, actor.y]
            and not getattr(actor, "invulnerable", False)
            and type(actor.ai).__name__ != "Vendor"
            for actor in game_map.actors
        )
        self.engine.player.fighter.regenerate_hp(in_combat)
        from events import tick

        tick(self.engine.game_map)  # delayed level editor events
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


def stat_lines(player) -> list:
    """(label, value) rows of the stats screen, at most five."""
    fighter = player.fighter
    kind = fighter.main_stat_kind
    lines = []
    if kind:
        lines.append((stats.STAT_NAMES[kind], fighter.stat))
    lines.append(("Max HP", fighter.max_hp))
    attacks = f"  x{fighter.attack_count}" if fighter.attack_count > 1 else ""
    lines.append(("Melee damage", f"{fighter.power}{attacks}"))
    lines.append(("Armor", fighter.armor))
    if kind == stats.DEX:
        lines.append(("Dodge", f"{fighter.dodge}%"))
    elif kind == stats.INT:
        lines.append(("Spell damage", f"+{fighter.spell_bonus}"))
    elif kind == stats.STR:
        lines.append(("Mass level", fighter.mass_level))
    return lines


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
        for row, (label, value) in enumerate(stat_lines(self.engine.player)):
            console.print(
                x=x + 1,
                y=8 + affix_max_len + row,
                text=f"{label:<20}: {value}",
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
    """Level up: HP and resources refill, +1 main stat and the player picks
    one of a few affixes (components/affix.py). The offers are rolled once
    when the screen opens; only picking one closes it."""

    TITLE = "Level Up"
    WIDTH = 50
    FIRST_CHOICE_ROW = 5

    def __init__(self, engine):
        super().__init__(engine)
        new_level = engine.player.level.current_level + 1
        self.choices = engine.affixManager.roll_choices(level=new_level)
        engine.player.fighter.reset_self()

    @property
    def x(self) -> int:
        return 30 if self.engine.player.x <= 30 else 0

    def on_render(self, console):
        super().on_render(console)
        x = self.x
        console.draw_frame(
            x=x,
            y=0,
            width=self.WIDTH,
            height=self.FIRST_CHOICE_ROW + len(self.choices) + 2,
            title=self.TITLE,
            clear=True,
            fg=(255, 255, 255),
            bg=(0, 0, 0),
        )
        console.print(x=x + 1, y=1, string="The tower grants you power")
        kind = self.engine.player.fighter.main_stat_kind
        if kind:
            console.print(x=x + 1, y=2, string=f"+{stats.LEVEL_UP_STAT} {stats.STAT_NAMES[kind]}")
        console.print(x=x + 1, y=self.FIRST_CHOICE_ROW - 1, string="Choose one:")
        for i, affix in enumerate(self.choices):
            console.print(
                x=x + 2,
                y=self.FIRST_CHOICE_ROW + i,
                string=f"{chr(ord('a') + i)}) {affix.AFFIX_NAME}",
                fg=affix.AFFIX_COLOR.value,
            )

    def pick(self, index: int):
        if not 0 <= index < len(self.choices):
            return None
        player = self.engine.player
        if player.fighter.main_stat_kind:
            player.fighter.main_stat += stats.LEVEL_UP_STAT
        self.engine.affixManager.gain_affix(self.choices[index])
        player.level.increase_level()
        return MainGameEventHandler(self.engine)

    def ev_keydown(self, event):
        key = event.sym
        if tcod.event.KeySym.A <= key <= tcod.event.KeySym.Z:
            return self.pick(key - tcod.event.KeySym.A)
        if tcod.event.KeySym.N1 <= key <= tcod.event.KeySym.N9:
            return self.pick(key - tcod.event.KeySym.N1)
        return None  # level up is mandatory: other keys do nothing

    def ev_mousebuttondown(self, event):
        from level_editor import event_tile

        tile = event_tile(event)
        if tile is None:
            return None
        x, y = tile
        if self.x <= x < self.x + self.WIDTH:
            return self.pick(y - self.FIRST_CHOICE_ROW)
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
        real_price = item.price
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


def pause_menu(game: EventHandler, extra_options=()) -> BaseEventHandler:
    """Esc in game. extra_options are added on top, e.g. a later "back to editor"."""
    engine = game.engine

    def save() -> bool:
        try:
            engine.save_as("savegame.sav")
            return True
        except Exception as exc:
            print(f"Saving failed: {exc}")
            return False

    def to_main_menu():
        from setup_game import MainMenu

        save()
        return MainMenu()

    def quit_game():
        save()
        # saved already; the main loop would not save from this menu anyway
        raise exceptions.QuitWithoutSaving()

    k = tcod.event.KeySym
    options = list(extra_options) + [
        (k.R, "Resume", lambda: game),
        (k.M, "Save and main menu", to_main_menu),
        (k.Q, "Save and quit", quit_game),
    ]
    return ChoicePopup(game, "Paused", options)


def resume_game(engine: Engine) -> BaseEventHandler:
    """Back to playing, unless an event queued a lore page to read first."""
    page = getattr(engine, "pending_screen", None)
    if page is not None:
        engine.pending_screen = None
        return ReadingScreen(engine, page)
    return MainGameEventHandler(engine)


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

        for movement_id in MOVE_KEYS:
            if movement_id in DIAGONAL_MOVES and not stats.PLAYER_DIAGONALS:
                continue
            c_event = get_event_by_id(movement_id)
            if c_event["ID"] in MOVE_KEYS and key == c_event["KEY"]:
                dx, dy = MOVE_KEYS[c_event["ID"]]
                # if player ist rouge they can sprint this consumes stamina. in order to sprint the input is multiplied by 2
                if (
                    self.engine.player.player_class == PlayerClass.ROUGE
                    and tcod.event.Modifier(c_event["MOD"]) in modifier
                    and self.engine.player.fighter.stamina >= self.engine.player.fighter.sprint_cost
                ):
                    dx = dx * 2
                    dy = dy * 2
                    # stamina is handled by the bump action
                else:
                    # not sprinting: regain stamina per step, more with DEX
                    fighter = self.engine.player.fighter
                    fighter.stamina = min(
                        fighter.max_stamina, fighter.stamina + fighter.stamina_regen
                    )
                return BumpAction(player, dx, dy)
            elif key in WAIT_KEYS:
                return WaitAction(player)

        c_event = get_event_by_id(5)
        if key == tcod.event.KeySym(c_event["KEY"]) and modifier == tcod.event.Modifier(
            c_event["MOD"]
        ):
            return pause_menu(self)

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
            return cheat_spawn_picker(self.engine, "Spawn item", ("items", "equipment"))
        elif key == tcod.event.KeySym.F2 and CHEATS:
            return cheat_spawn_picker(self.engine, "Spawn monster", ("actors",))
        elif key == tcod.event.KeySym.F3 and CHEATS:
            return toggle_cheat_picker(self.engine)
        elif key == tcod.event.KeySym.F4 and CHEATS:
            return action_cheat_picker(self.engine)
        elif key == tcod.event.KeySym.F5 and CHEATS:
            return affix_cheat_picker(self.engine)
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
                    if slot.equippable.armor_bonus != 0:
                        line = line + f" Armor: {slot.equippable.armor_bonus}"
                    if slot.equippable.power_bonus != 0:
                        line = line + f" Attack: {slot.equippable.power_bonus}"
                    console.print(x=x + 13, y=y, string=line)
                    x += 13
                    x = x_save

                y += 2


def cheat_spawn_picker(engine: Engine, title: str, categories) -> "ListPicker":
    """F1 / F2: every entity of these data categories (Data/*.json, so new and
    edited entities are included), filterable. Enter spawns one; the list
    stays open for more, Esc closes it."""
    import entity_data
    import entity_factory

    def short_name(entity_id) -> str:
        # class corpses carry their description in the name
        return getattr(entity_factory, entity_id).name.split("  ")[0].strip()

    entries = [
        (f"{entity_data.CATEGORIES[category]}: {short_name(entity_id)} ({entity_id})", entity_id)
        for category in categories
        for entity_id, entry_category in entity_factory.CATEGORY.items()
        if entry_category == category and entity_id != entity_factory.PLAYER_ID
    ]

    def spawn(entity_id):
        from entity import Actor

        prototype = getattr(entity_factory, entity_id, None)
        if prototype is None:
            return None
        spot = cheat_spawn_spot(engine, actor=isinstance(prototype, Actor))
        if spot is None:
            engine.message_log.add_message("No free tile next to you.", color.invalid)
            return None
        prototype.spawn(engine.game_map, *spot)
        engine.message_log.add_message(f"The Tower creates 1 {short_name(entity_id)}")
        return None

    return ListPicker(MainGameEventHandler(engine), title, entries, spawn)


def cheat_spawn_spot(engine: Engine, actor: bool):
    """Items land under the player; actors on the nearest free walkable tile."""
    player = engine.player
    if not actor:
        return player.x, player.y
    game_map = engine.game_map
    for radius in (1, 2, 3):
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                x, y = player.x + dx, player.y + dy
                if (
                    max(abs(dx), abs(dy)) == radius
                    and game_map.in_bounds(x, y)
                    and game_map.tiles["walkable"][x, y]
                    and not game_map.get_blocking_entity_at_location(x, y)
                ):
                    return x, y
    return None


def toggle_cheat_picker(engine: Engine) -> "ListPicker":
    """F3: switch the GENERAL_CHEATS on and off; the list stays open."""

    def entries():
        return [
            (f"{name.replace('_', ' ').capitalize():<12} {'ON' if on else 'off'}", name)
            for name, on in GENERAL_CHEATS.items()
        ]

    def toggle(name):
        if name is None:
            return None
        GENERAL_CHEATS[name] = not GENERAL_CHEATS[name]
        picker.all_items = entries()
        state = "on" if GENERAL_CHEATS[name] else "off"
        engine.message_log.add_message(f"Cheat {name.replace('_', ' ')} {state}")
        return None

    picker = ListPicker(MainGameEventHandler(engine), "Cheat toggles", entries(), toggle)
    return picker


def action_cheat_picker(engine: Engine) -> "ListPicker":
    """F4: one-off cheats from GENERAL_CHEAT_ACTIVATIONS."""
    labels = {
        "spawn_shop": "Go to a shop room",
        "current_floor_+": "Floor +1",
        "current_floor_-": "Floor -1",
        "level_up": "Level up",
        "die": "Die",
    }

    def entries():
        floor = engine.game_world.current_floor
        return [
            (labels.get(name, name) + (f"  (floor {floor})" if name.startswith("current_floor") else ""), name)
            for name in GENERAL_CHEAT_ACTIVATIONS
        ]

    def run(name):
        from procgen import generate_shop_room

        match name:
            case "spawn_shop":
                engine.game_map = generate_shop_room(
                    engine=engine,
                    map_width=100,
                    map_height=100,
                    current_floor=engine.game_world.current_floor,
                )
                engine.update_fov()
                return MainGameEventHandler(engine)
            case "current_floor_+":
                engine.game_world.current_floor += 1
            case "current_floor_-":
                engine.game_world.current_floor -= 1
            case "level_up":
                engine.player.level.current_xp = engine.player.level.xp_to_next_level
                return LevelUpEventHandler(engine=engine)
            case "die":
                engine.player.fighter.die()
                return GameOverEventHandler(engine)
        picker.all_items = entries()
        return None

    picker = ListPicker(MainGameEventHandler(engine), "Cheat actions", entries(), run)
    return picker


def affix_cheat_picker(engine: Engine) -> "ListPicker":
    """F5: every affix of the affix table, for any class, rolled once for the
    current level when the list opens. Enter grants exactly what is shown;
    the list stays open for more."""
    from components.affix import AFFIX_TABLE

    rolled = [engine.affixManager.make(row) for row in AFFIX_TABLE]
    entries = [
        (f"{affix.AFFIX_COLOR.name.capitalize():<9} {affix.AFFIX_NAME}", index)
        for index, affix in enumerate(rolled)
    ]

    def grant(index):
        if index is None:
            return None
        gained = copy.deepcopy(rolled[index])
        engine.affixManager.gain_affix(gained)
        engine.message_log.add_message(f"The Tower grants you {gained.AFFIX_NAME}")
        return None

    return ListPicker(MainGameEventHandler(engine), "Grant affix", entries, grant)



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


def rank_matches(query: str, labels: list) -> list:
    """Indexes of the labels matching query: starts-with first, then contains.
    Case and spaces vs underscores are ignored."""
    def norm(text):
        return text.strip().lower().replace(" ", "_")

    query = norm(query)
    if not query:
        return list(range(len(labels)))
    starts = [i for i, label in enumerate(labels) if norm(label).startswith(query)]
    contains = [i for i, label in enumerate(labels) if query in norm(label) and i not in starts]
    return starts + contains


def id_suggestions(counts) -> list:
    """[(id, uses)] -> autocomplete entries for TextPrompt, e.g. ('gate', 'gate  (3)')."""
    return [(value, f"{value}  ({uses})" if uses else value) for value, uses in counts]


class TextPrompt(BaseEventHandler):
    MAX_SUGGESTIONS = 8

    def __init__(
        self,
        parent: BaseEventHandler,
        title: str,
        text: str,
        on_submit: Callable[[str], Optional[BaseEventHandler]],
        suggestions: Optional[list] = None,
        max_length: int = NAME_MAX_LENGTH,
        any_char: bool = False,  # punctuation too, not only name characters
    ):
        self.parent = parent
        self.title = title
        self.text = text
        self.on_submit = on_submit
        self.error = ""
        self.suggestions = suggestions or []  # [(value, label)], autocomplete for ids
        self.highlight: Optional[int] = None  # picked with Up/Down
        self.max_length = max_length
        self.any_char = any_char

    def matches(self) -> list:
        indexes = rank_matches(self.text, [value for value, _ in self.suggestions])
        return [self.suggestions[i] for i in indexes[: self.MAX_SUGGESTIONS]]

    def on_render(self, console):
        self.parent.on_render(console)
        dim(console)
        width = min(self.max_length + 8, console.width - 2)
        matches = self.matches() if self.suggestions else []
        list_rows = len(matches) + 1 if matches else 0
        x, y = draw_box(console, width, 7 + list_rows, self.title)
        console.print(x + 2, y + 2, (self.text + "_")[-(width - 4):].ljust(width - 4),
                      fg=color.menu_title, bg=(40, 10, 10))
        for i, (_, label) in enumerate(matches):
            text = f" {label}"[: width - 4].ljust(width - 4)
            bg = (90, 20, 20) if i == self.highlight else color.black
            console.print(x + 2, y + 3 + i, text, fg=color.menu_text, bg=bg)
        hint = "[Tab] fill  [Enter] ok" if matches else "[Enter] ok  [Esc] cancel"
        console.print(x + 2, y + 4 + list_rows, hint, fg=color.impossible)
        if self.error:
            console.print(x + 2, y + 5 + list_rows, self.error[: width - 4], fg=color.error)

    def ev_keydown(self, event):
        key = event.sym
        k = tcod.event.KeySym
        if key == k.ESCAPE:
            return self.parent
        matches = self.matches() if self.suggestions else []
        if self.highlight is not None and self.highlight >= len(matches):
            self.highlight = None
        if key in CONFIRM_KEYS:
            if self.highlight is not None:  # a suggestion picked with the arrows
                return self.on_submit(matches[self.highlight][0])
            return self.on_submit(self.text.strip())
        if matches and key in (k.UP, k.DOWN):
            step = -1 if key == k.UP else 1
            start = -1 if self.highlight is None and step == 1 else (self.highlight or 0)
            self.highlight = (start + step) % len(matches)
            return None
        if matches and key == k.TAB:
            self.text = matches[self.highlight or 0][0]
            self.highlight = None
            return None
        if key == k.BACKSPACE:
            self.text = self.text[:-1]
            self.error = ""
            self.highlight = None
            return None
        char = typed_char(event) if self.any_char else key_to_char(event)
        if char and len(self.text) < self.max_length:
            self.text += char
            self.error = ""
            self.highlight = None
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
    MAX_ROWS = 30  # longer lists scroll
    MAX_WIDTH = 76

    def __init__(self, parent, title, items, on_pick):
        self.parent = parent
        self.title = title
        self.all_items = items  # [(label, value)], value None stays on top while filtering
        self.on_pick = on_pick
        self.selected = 0
        self.scroll = 0
        self.query = ""  # typed filter

    @property
    def items(self) -> list:
        pinned = [item for item in self.all_items if item[1] is None]
        rest = [item for item in self.all_items if item[1] is not None]
        if not self.query:
            return pinned + rest
        return pinned + [rest[i] for i in rank_matches(self.query, [d for d, _ in rest])]

    @property
    def rows(self) -> int:
        return max(1, min(len(self.items), self.MAX_ROWS))

    def on_render(self, console):
        self.parent.on_render(console)
        dim(console)
        items = self.items
        width = max([len(self.title) + 4] + [len(d) + 6 for d, _ in self.all_items]) + 4
        width = min(width, self.MAX_WIDTH)
        top = 1 if self.query else 0  # the filter line
        scrolls = len(items) > self.rows
        x, y = draw_box(console, width, self.rows + top + (5 if scrolls else 4), self.title)
        if self.query:
            console.print(x + 2, y + 1, f"Filter: {self.query}_"[: width - 4], fg=color.menu_title)
        if not items:
            text = "No match" if self.query else "Nothing here"
            console.print(x + 2, y + 2 + top, text, fg=color.impossible)

        # keep the selection in view
        if self.selected < self.scroll:
            self.scroll = self.selected
        elif self.selected >= self.scroll + self.rows:
            self.scroll = self.selected - self.rows + 1
        visible = items[self.scroll : self.scroll + self.rows]
        for row, (display, _) in enumerate(visible):
            text = f" {display}"[: width - 4].ljust(width - 4)
            row_y = y + 2 + top + row
            if self.scroll + row == self.selected:
                console.print(x + 2, row_y, text, fg=color.menu_title, bg=(90, 20, 20))
            else:
                console.print(x + 2, row_y, text)
        hint = f"{self.selected + 1}/{len(items)}  PgUp/PgDn" if scrolls else ""
        if not self.query and len(self.all_items) > 5:
            hint = (hint + "  type to filter").strip()
        if hint:
            console.print(x + 2, y + self.rows + top + 3, hint[: width - 4], fg=color.impossible)

    def ev_mousewheel(self, event):
        items = self.items
        if items:
            step = -3 if event.y > 0 else 3
            self.selected = max(0, min(len(items) - 1, self.selected + step))
        return None

    def set_query(self, query: str) -> None:
        self.query = query
        self.scroll = 0
        # select the first match, not a pinned entry like "+ New text..."
        pinned = sum(1 for _, value in self.all_items if value is None)
        self.selected = pinned if query and len(self.items) > pinned else 0

    def ev_keydown(self, event):
        key = event.sym
        k = tcod.event.KeySym
        if key == k.ESCAPE:
            if self.query:  # first Esc clears the filter
                self.set_query("")
                return None
            return self.parent
        if key == k.BACKSPACE:
            self.set_query(self.query[:-1])
            return None
        char = key_to_char(event)
        if char:
            self.set_query(self.query + char)
            return None
        items = self.items
        if not items:
            return None
        if key == k.UP:
            self.selected = (self.selected - 1) % len(items)
        elif key == k.DOWN:
            self.selected = (self.selected + 1) % len(items)
        elif key == k.PAGEUP:
            self.selected = max(0, self.selected - self.rows)
        elif key == k.PAGEDOWN:
            self.selected = min(len(items) - 1, self.selected + self.rows)
        elif key == k.HOME:
            self.selected = 0
        elif key == k.END:
            self.selected = len(items) - 1
        elif key in CONFIRM_KEYS:
            return self.on_pick(items[self.selected][1])
        return None

class PropertyMenu(BaseEventHandler):
    def __init__(self, editor, pos, fields, values=None, title="Properties",
                 on_close=None, part_of_level=True):
        self.editor = editor  # the LevelEditor, also the screen we return to
        self.pos = pos  # None for things without a cell, e.g. area triggers
        self._fields = fields  # [(key, kind)], or values -> [(key, kind)]
        self._values = values  # props stored elsewhere than level.properties[pos]
        self.title = title
        self.on_close = on_close  # () -> handler on Esc, e.g. saving an entity
        self.part_of_level = part_of_level  # changes make the level unsaved
        self.selected = 0

    @property
    def fields(self):
        fields = self._fields(self.values) if callable(self._fields) else self._fields
        self.selected = min(self.selected, len(fields) - 1)
        return fields

    @property
    def values(self):
        if self._values is not None:
            return self._values
        return self.editor.level.properties.setdefault(self.pos, {})

    def set_value(self, key, value):
        self.values[key] = value
        if self.part_of_level:
            self.editor.dirty = True
        return self

    def clear_value(self, key):
        self.values.pop(key, None)
        if self.part_of_level:
            self.editor.dirty = True
        return self

    def on_render(self, console):
        self.editor.on_render(console)
        dim(console)
        width = 44
        x, y = draw_box(console, width, len(self.fields) + 5, self.title)
        for i, (key, kind) in enumerate(self.fields):
            value = self.values.get(key, "-")
            text = f" {key}: {value}"[: width - 4].ljust(width - 4)
            bg = (90, 20, 20) if i == self.selected else color.black
            console.print(x + 2, y + 2 + i, text, bg=bg)
        console.print(x + 2, y + len(self.fields) + 3, "[Enter] edit  [Esc] done", fg=color.impossible)

    def ev_keydown(self, event):
        key = event.sym
        if key == tcod.event.KeySym.ESCAPE:
            return self.on_close() if self.on_close else self.editor
        if key == tcod.event.KeySym.UP:
            self.selected = (self.selected - 1) % len(self.fields)
        elif key == tcod.event.KeySym.DOWN:
            self.selected = (self.selected + 1) % len(self.fields)
        elif key in CONFIRM_KEYS:
            return self.edit(*self.fields[self.selected])
        return None

    def text_file_field(self, key, folder, files, what, built_in=(), template="",
                        suggestions=None, check=None):
        """A field naming a text file in folder (lore, loot tables): pick one,
        create a new one or edit it in place.
        built_in: extra (label, value) entries that are not files.
        check: text -> problems, shown after saving."""
        import id_index

        def open_editor(filename, text):
            others = id_index.uses_of(key, filename, self.editor.level, self.pos)
            title = filename + (f" (used {len(others)}x more)" if others else "")

            def save(new_text):
                os.makedirs(folder, exist_ok=True)
                with open(os.path.join(folder, filename), "w", encoding="utf-8") as f:
                    f.write(new_text)
                result = self.set_value(key, filename)
                problems = check(new_text) if check else []
                if problems:
                    return PopupMessage(result, "Saved, but:\n" + "\n".join(problems[:10]),
                                        halved=True, alignment=libtcodpy.CENTER)
                return result

            return LoreEditor(self, title, text, save, suggestions=suggestions)

        def new_file():
            def submit(name):
                if not name:
                    prompt.error = f"The {what} needs a name"
                    return None
                problem = check_name(name)
                if problem:
                    prompt.error = problem
                    return None
                filename = name.replace(" ", "_") + ".txt"
                if os.path.exists(os.path.join(folder, filename)):
                    prompt.error = f"{name} already exists"
                    return None
                return open_editor(filename, template)  # file is written on save only

            prompt = TextPrompt(self, f"Name of the new {what}", "", submit)
            return prompt

        built_in_values = {value for _, value in built_in}

        def pick(filename):
            if filename is None:
                return new_file()
            if filename in built_in_values:
                return self.set_value(key, filename)

            def choose(choice):
                if choice == "use":
                    return self.set_value(key, filename)
                try:
                    with open(os.path.join(folder, filename), encoding="utf-8") as f:
                        text = f.read()
                except OSError as exc:
                    return PopupMessage(self, f"Can't read {filename}:\n{exc}",
                                        halved=True, alignment=libtcodpy.CENTER)
                return open_editor(filename, text)

            return ListPicker(self, filename, [("Use this", "use"), ("Edit", "edit")], choose)

        entries = [(f"+ New {what}...", None)] + list(built_in) + files
        return ListPicker(self, f"Choose {what}", entries, pick)

    def id_field(self, key, kind):
        """A flag, quest id or signal: autocomplete from the id index, then a
        popup of everything else that uses the same id."""
        import id_index
        from components.dialouge_parser import quest_key

        level = self.editor.level

        def submit(text):
            if not text:
                self.clear_value(key)
                return self
            value = quest_key(text)
            self.set_value(key, value)
            lines = id_index.describe(kind, value, self.field_role(key, kind), level, self.pos)
            return PopupMessage(self, "\n".join(lines), halved=True, alignment=libtcodpy.CENTER)

        suggestions = id_suggestions(id_index.suggestions(kind, level))
        return TextPrompt(self, key, self.values.get(key, ""), submit, suggestions=suggestions)

    def field_role(self, key, kind) -> str:
        """What this field does with its id: sends / receives, sets / reads, gives / uses."""
        if kind == "signal":
            if key == "signal" and self.pos is not None:
                from level_editor import tile_at

                tile = tile_at(self.editor.level, self.pos)
                if tile is not None and tile.link:
                    return tile.link
            return "sends"  # areas, target, on_death, on_pickup
        if kind == "flag":
            return "reads" if key in ("if", "ifnot") else "sets"
        return "gives" if key == "quest" else "uses"

    def edit(self, key, kind):
        if kind in ("flag", "quest", "signal"):
            return self.id_field(key, kind)
        if kind == "text":
            return TextPrompt(self, key, self.values.get(key, ""),
                              lambda text: self.set_value(key, text))
        if kind == "int":
            def submit_number(text):
                if not text:  # empty: back to the entity's own value
                    self.clear_value(key)
                    return self
                if not text.isdigit():
                    prompt.error = "Enter a whole number"
                    return None
                return self.set_value(key, text)

            prompt = TextPrompt(self, key, self.values.get(key, ""), submit_number)
            return prompt
        if kind == "signed_int":  # may be negative, e.g. organs to pay
            def submit_signed(text):
                if not text:
                    self.clear_value(key)
                    return self
                if not text.lstrip("-").isdigit():
                    prompt.error = "Enter a whole number, - to take"
                    return None
                return self.set_value(key, text)

            prompt = TextPrompt(self, key, self.values.get(key, ""), submit_signed, any_char=True)
            return prompt
        if kind == "gives":  # an item id from the data files, or a quest id
            import rules
            from components.dialouge_parser import quest_key
            import id_index
            from components.loot import item_names

            def submit_gives(text):
                if not text:
                    self.clear_value(key)
                    return self
                if rules.item_prototype(text) is not None:
                    return self.set_value(key, text)  # data ids keep their spelling
                return self.set_value(key, quest_key(text))

            suggestions = [(name, f"{name}  (item)") for name in item_names()]
            suggestions += id_suggestions(id_index.suggestions("quest", self.editor.level))
            return TextPrompt(self, f"{key} (item id or quest id)", self.values.get(key, ""),
                              submit_gives, suggestions=suggestions)
        if kind == "long_text":  # multi-line, e.g. the text of a message event
            return LoreEditor(self, key, self.values.get(key, ""),
                              lambda text: self.set_value(key, text))
        if kind.startswith("choice:"):
            options = kind[len("choice:"):].split(",")
            if len(options) > 6:  # too many to cycle through, pick from a list
                return ListPicker(self, key, [(option, option) for option in options],
                                  lambda option: self.set_value(key, option))
            current = self.values.get(key)
            index = options.index(current) + 1 if current in options else 0
            return self.set_value(key, options[index % len(options)])
        if kind == "name":  # longer than ids, any character
            return TextPrompt(self, key, self.values.get(key, ""),
                              lambda text: self.set_value(key, text) if text else self,
                              max_length=60, any_char=True)
        if kind == "char":
            def submit_char(text):
                if text.isdigit() and len(text) > 1:  # a tileset code, e.g. 9006
                    return self.set_value(key, chr(int(text)))
                if len(text) != 1:
                    prompt.error = "One character, or a code like 9006"
                    return None
                return self.set_value(key, text)

            prompt = TextPrompt(self, key, self.values.get(key, ""), submit_char, any_char=True)
            return prompt
        if kind == "color":
            def submit_color(text):
                try:
                    rgb = [int(part) for part in text.replace(" ", "").split(",")]
                except ValueError:
                    rgb = []
                if len(rgb) != 3 or not all(0 <= part <= 255 for part in rgb):
                    prompt.error = "Three numbers 0-255: r,g,b"
                    return None
                return self.set_value(key, ",".join(str(part) for part in rgb))

            prompt = TextPrompt(self, f"{key} (r,g,b)", self.values.get(key, ""),
                                submit_color, any_char=True)
            return prompt
        if kind == "entity":
            import entity_factory

            entries = [
                (f"{group}: {entity_factory.short_name(prototype)}", attr)
                for group, items in entity_factory.build_palette().items()
                for attr, prototype in items
            ]
            return ListPicker(self, "Choose entity", entries,
                              lambda attr: self.set_value(key, attr))
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

            return self.text_file_field(key, LORE_DIR, list_lore(), "text")
        if kind == "loot_table":
            from components import loot
            from components.settings import LOOT_DIR

            def check(text):
                return loot.parse(text).problems

            return self.text_file_field(
                key, LOOT_DIR, loot.list_loot_tables(), "loot table",
                built_in=[("random (floor loot)", loot.RANDOM_TABLE)],
                template=loot.TEMPLATE,
                suggestions=loot.item_names() + ["rolls:"],
                check=check,
            )
        if kind == "bool":
            from level_editor import is_yes

            return self.set_value(key, "no" if is_yes(self.values.get(key)) else "yes")
        return None

class LoreEditor(BaseEventHandler):
    """Multi-line text editor for lore files, used from the level editor."""

    WIDTH = 56  # same box as ReadingScreen, so lines wrap like they will in game
    ROWS = 30
    CURSOR_BG = (150, 40, 40)

    def __init__(self, parent, title, text, on_save, suggestions=None):
        self.parent = parent
        self.title = title
        self.on_save = on_save  # (text) -> handler, writes the file
        self.lines = text.split("\n") if text else [""]
        self.row = 0
        self.col = 0
        self.scroll = 0
        self.dirty = False
        self.error = ""
        # words offered for the first word of a line, e.g. item names in loot tables
        self.suggestions = suggestions or []
        self.completing = None  # (matches, index, word start) while Tab cycles

    def word_at_cursor(self):
        """(start, word) when the cursor is at the end of a line's first word."""
        before = self.lines[self.row][: self.col]
        word = before.lstrip()
        if not self.suggestions or not word or word.startswith("#") or " " in word:
            return None
        return len(before) - len(word), word

    def completions(self) -> list:
        found = self.word_at_cursor()
        if found is None:
            return []
        matches = [self.suggestions[i] for i in rank_matches(found[1], self.suggestions)]
        return [match for match in matches if match != found[1]][:6]

    def complete(self) -> None:
        """Tab: fill in the best match, pressing again cycles through the others."""
        if self.completing:
            matches, index, start = self.completing
            index = (index + 1) % len(matches)
        else:
            matches = self.completions()
            if not matches:
                return
            index, start = 0, self.word_at_cursor()[0]
        line = self.lines[self.row]
        self.lines[self.row] = line[:start] + matches[index] + line[self.col :]
        self.col = start + len(matches[index])
        self.completing = (matches, index, start)
        self.dirty = True

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

        # autocomplete list under the cursor
        if self.completing:
            matches, highlight = self.completing[0], self.completing[1]
        else:
            matches, highlight = self.completions(), None
        if matches:
            width = max(len(match) for match in matches) + 2
            px = min(cx, console.width - width)
            for i, match in enumerate(matches):
                if cy + 1 + i >= console.height:
                    break
                bg = (90, 20, 20) if i == highlight else (40, 40, 40)
                console.print(px, cy + 1 + i, f" {match}".ljust(width), fg=color.menu_text, bg=bg)

        if self.error:
            console.print(x + 2, y + self.ROWS + 3, self.error[: self.WIDTH - 4], fg=color.error)
        else:
            hint = "[Ctrl+S] save  [Esc] back"
            if self.suggestions:
                hint += "  [Tab] complete"
            console.print(x + 2, y + self.ROWS + 3, hint, fg=color.impossible)

    def ev_keydown(self, event):
        key = event.sym
        k = tcod.event.KeySym
        self.error = ""
        if key != k.TAB:
            self.completing = None
        if event.mod & CTRL:
            if key == k.S:
                return self.save()
            return None
        if key == k.ESCAPE:
            return self.leave()
        if key == k.TAB:
            self.complete()
        elif key in CONFIRM_KEYS:
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

class DialogueScreen(AskUserEventHandler):
    WIDTH = 50

    def __init__(self, engine, npc):
        super().__init__(engine)
        self.npc = npc
        self.dialogue = npc.dialogue
        # passages whose gives/takes already ran for this NPC
        if not hasattr(npc, "dialogue_done"):
            npc.dialogue_done = set()
        self.enter(self.opening_passage())

    def opening_passage(self) -> str:
        """The first passage tagged "start" whose conditions hold (e.g. a
        different greeting once a flag is set), else the story's start."""
        for passage in self.dialogue.passages.values():
            if "start" in passage.tags and self.can_enter(passage.name):
                return passage.name
        return self.dialogue.start

    def can_enter(self, name: str) -> bool:
        """if: / ifnot: / requires: tags, the same conditions as in levels."""
        import rules

        tags = self.dialogue.passages[name].tags
        return rules.conditions_met(self.engine, rules.conditions_from_tags(tags))

    def enter(self, name: str) -> None:
        """Shows a passage and runs its action tags (rules.ACTIONS: gives:,
        takes:, organs:, signal:, flag:, unflag:, die, spawn:, lore:, ...)
        in the order written. A passage that did something only does it once
        per NPC."""
        import rules

        self.current = name
        if name in self.npc.dialogue_done:
            return
        actions = rules.tag_actions(self.passage.tags)
        ctx = rules.context(self.engine, self.engine.game_map, (self.npc.x, self.npc.y), npc=self.npc)
        for action, props in actions:
            rules.run_action(action, ctx, props)
        if actions:
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
            return resume_game(self.engine)

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
            return resume_game(self.engine)
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