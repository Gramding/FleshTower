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
from components.settings import CHEATS, GENERAL_CHEATS, GENERAL_CHEAT_ACTIVATIONS
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

    def on_render(self, console: tcod.console.Console):
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
            height=27,
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
        # TODO dispaly new modifiers
        console.draw_rect(
            x=x + 1,
            y=15,
            width=width - 2,
            height=1,
            ch=ord("─"),
            fg=(255, 255, 255),
            bg=(0, 0, 0),
            bg_blend=libtcodpy.BKGND_MULTIPLY,
        )
        console.print(
            x + 1,
            15,
            text="┤Behavioral Deviations├",
            alignment=libtcodpy.CENTER,
            width=width - 2,
            height=1,
        )
        text = "Meele Damage"
        console.print(
            x=x + 1,
            y=17,
            text=f"{text:<20}: {self.engine.player.fighter.power}",
        )
        text = "Damage Reduction"
        console.print(
            x=x + 1,
            y=18,
            text=f"{text:<20}: {self.engine.player.fighter.damage_reduction}",
        )
        text = "Spell Damage"
        console.print(
            x=x + 1,
            y=19,
            text=f"{text:<20}: {self.engine.player.fighter.spell_damage_bonus}",
        )
        text = "Price Discount"
        console.print(
            x=x + 1,
            y=20,
            text=f"{text:<20}: {self.engine.player.fighter.price_discount}",
        )
        text = "Attack Count"
        console.print(
            x=x + 1,
            y=21,
            text=f"{text:<20}: {self.engine.player.fighter.attack_count}",
        )

    def ev_keydown(self, event):
        key = event.sym
        mod = event.mod
        if key == tcod.event.KeySym.E and mod == tcod.event.Modifier.LCTRL:
            for i in self.engine.player.equipment.__dict__:
                if "_" not in i and "parent" not in i:
                    slot = getattr(self.engine.player.equipment, i)
                    if slot:
                        self.engine.player.equipment.unequip_from_slot(i, True)

        return super().ev_keydown(event)


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
        console.print(x=x + 1, y=2, string="Select the towers blessing")

        self.affix = random_affix = self.engine.affixManager.rand_affix()

        console.print(
            x=x + 1,
            y=4,
            string=random_affix.AFFIX_NAME,
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


class MainGameEventHandler(EventHandler):
    def ev_keydown(self, event: tcod.event.KeyDown) -> Optional[ActionOrHandler]:
        action: Optional[Action] = None

        key = event.sym
        modifier = event.mod

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
            and "Organ" in target.name
        ):
            return ShopActivateHandler(engine=self.engine, target=target)

        for movement_id in range(100, 104):
            c_event = get_event_by_id(movement_id)
            if c_event["ID"] in MOVE_KEYS and key == c_event["KEY"]:
                dx, dy = MOVE_KEYS[c_event["ID"]]
                # if player ist rouge they can sprint this consumes stamina. in order to sprint the input is multiplied by 2
                if (
                    self.engine.player.is_rouge
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
