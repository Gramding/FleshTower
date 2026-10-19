"""Affixes: the bonuses picked on level-up.

AFFIX_TABLE below lists every affix that can be rolled: its value range and
whether flat values grow with the player level (components/stats.py:
AFFIX_LEVEL_SCALING). The pool is the class's CLASS_LOCK (GENERIC = everyone),
the rarity its AFFIX_COLOR. How offers are rolled (pool chance, rarity weights,
number of choices) is in components/stats.py too.

To add an affix: subclass Affix, give it AFFIX_COLOR, apply_affix and
describe, and add a row to AFFIX_TABLE.

Class names stay as they are: savegames store affixes by class name.
"""
import math
import random
from typing import List, Optional

from color import AffixColor
from components import stats
from components.settings import PlayerClass
from message_log import MessageLog


class Affix:
    AFFIX_NAME = ""
    CLASS_LOCK = PlayerClass.GENERIC
    AFFIX_COLOR = AffixColor.COMMON

    def __init__(self, value=None, stat_name: str = "") -> None:
        self.value = value
        self.stat_name = stat_name  # the player's main stat when rolled
        self.is_set = False
        self.AFFIX_NAME = self.describe()

    def describe(self) -> str:
        return type(self).AFFIX_NAME

    def apply_affix(self, engine):
        self.is_set = True


# --- everyone ---


class FlatMeeleIncrease(Affix):
    """+value main stat (STR, DEX or INT)."""

    AFFIX_COLOR = AffixColor.COMMON

    def describe(self):
        return f"+{self.value} {self.stat_name}"

    def apply_affix(self, engine):
        engine.player.fighter.bonus_stat += self.value
        super().apply_affix(engine)


class PercentMeeleIncrease(Affix):
    """+value% main stat."""

    AFFIX_COLOR = AffixColor.RARE

    def describe(self):
        return f"+{self.value:.0%} {self.stat_name}"

    def apply_affix(self, engine):
        fighter = engine.player.fighter
        fighter.bonus_stat += math.ceil(fighter.stat * self.value)
        super().apply_affix(engine)


class FlatHPIncrease(Affix):
    AFFIX_COLOR = AffixColor.COMMON

    def describe(self):
        return f"+{self.value} Max HP"

    def apply_affix(self, engine):
        engine.player.fighter.bonus_hp += self.value
        super().apply_affix(engine)


class PercentHPIncrease(Affix):
    AFFIX_COLOR = AffixColor.UNCOMMON

    def describe(self):
        return f"+{self.value:.0%} Max HP"

    def apply_affix(self, engine):
        fighter = engine.player.fighter
        fighter.bonus_hp += math.ceil(fighter.max_hp * self.value)
        super().apply_affix(engine)


class FlatAttacCountIncrease(Affix):
    AFFIX_COLOR = AffixColor.LEGENDARY

    def describe(self):
        return f"+{self.value} Attack per turn"

    def apply_affix(self, engine):
        engine.player.fighter.bonus_attacks += self.value
        super().apply_affix(engine)


class XPIncrease(Affix):
    AFFIX_NAME = "XP Increase"
    AFFIX_COLOR = AffixColor.UNCOMMON

    def apply_affix(self, engine):
        engine.player.level.add_xp(
            random.randint(
                int(engine.player.level.xp_to_next_level / 2),
                int(engine.player.level.xp_to_next_level * 2),
            )
        )
        super().apply_affix(engine)


class LuckyIncrease(Affix):
    """value random extra affixes (never Lucky again)."""

    AFFIX_COLOR = AffixColor.LEGENDARY

    def describe(self):
        return f"Lucky: {self.value} random affixes"

    def apply_affix(self, engine):
        super().apply_affix(engine)
        manager = engine.affixManager
        for _ in range(self.value):
            manager.gain_affix(manager.roll(exclude={LuckyIncrease}))


# --- Helixbound ---


class FlatMANAIncrease(Affix):
    CLASS_LOCK = PlayerClass.MAGE
    AFFIX_COLOR = AffixColor.COMMON

    def describe(self):
        return f"+{self.value} Max Mana"

    def apply_affix(self, engine):
        engine.player.fighter.bonus_mana += self.value
        super().apply_affix(engine)


class PercentMANAIncrease(Affix):
    CLASS_LOCK = PlayerClass.MAGE
    AFFIX_COLOR = AffixColor.UNCOMMON

    def describe(self):
        return f"+{self.value:.0%} Max Mana"

    def apply_affix(self, engine):
        fighter = engine.player.fighter
        fighter.bonus_mana += math.ceil(fighter.max_mana * self.value)
        super().apply_affix(engine)


class ManaRegenIncrease(Affix):
    CLASS_LOCK = PlayerClass.MAGE
    AFFIX_COLOR = AffixColor.RARE

    def describe(self):
        return f"Mana returns {self.value} turn faster"

    def apply_affix(self, engine):
        engine.player.fighter.bonus_mana_regen += self.value
        super().apply_affix(engine)


# --- Whisperbound ---


class FlatStaminaIncrease(Affix):
    CLASS_LOCK = PlayerClass.ROUGE
    AFFIX_COLOR = AffixColor.COMMON

    def describe(self):
        return f"+{self.value} Max Stamina"

    def apply_affix(self, engine):
        engine.player.fighter.bonus_stamina += self.value
        super().apply_affix(engine)


class PercentStaminaIncrease(Affix):
    CLASS_LOCK = PlayerClass.ROUGE
    AFFIX_COLOR = AffixColor.UNCOMMON

    def describe(self):
        return f"+{self.value:.0%} Max Stamina"

    def apply_affix(self, engine):
        fighter = engine.player.fighter
        fighter.bonus_stamina += math.ceil(fighter.max_stamina * self.value)
        super().apply_affix(engine)


class SprintCostDecrease(Affix):
    CLASS_LOCK = PlayerClass.ROUGE
    AFFIX_COLOR = AffixColor.RARE

    def describe(self):
        lunge = self.value * stats.LUNGE_DISCOUNT_FACTOR
        return f"Sprint costs {self.value} less, lunge {lunge} less"

    def apply_affix(self, engine):
        engine.player.fighter.sprint_discount += self.value
        super().apply_affix(engine)


# --- Gorebound ---


class MassGainIncrease(Affix):
    CLASS_LOCK = PlayerClass.FIGHTER
    AFFIX_COLOR = AffixColor.UNCOMMON

    def describe(self):
        return f"+{self.value} Mass per corpse"

    def apply_affix(self, engine):
        engine.player.fighter.bonus_mass_gain += self.value
        super().apply_affix(engine)


class InstantMassIncrease(Affix):
    CLASS_LOCK = PlayerClass.FIGHTER
    AFFIX_COLOR = AffixColor.COMMON

    def describe(self):
        return f"Gain {self.value} Mass"

    def apply_affix(self, engine):
        engine.player.fighter.gain_mass(self.value)
        super().apply_affix(engine)


class MassArmorIncrease(Affix):
    CLASS_LOCK = PlayerClass.FIGHTER
    AFFIX_COLOR = AffixColor.RARE

    def describe(self):
        return f"Dense flesh: +{self.value} Armor per Mass level"

    def apply_affix(self, engine):
        engine.player.fighter.bonus_mass_armor += self.value
        super().apply_affix(engine)


# --- no longer rolled (armor comes from gear and mass), kept so older
# savegames that contain them still load ---


class FlatDamageReductionIncrease(Affix):
    AFFIX_COLOR = AffixColor.RARE


class PercentDamageReductionIncrease(Affix):
    AFFIX_COLOR = AffixColor.RARE


# (affix, low, high, scales with level). Percent affixes roll fractions
# (0.05 = 5%) and never scale; flat values use stats.scaled().
AFFIX_TABLE = [
    # everyone
    (FlatMeeleIncrease, 1, 2, False),  # was scaling (True)
    # (PercentMeeleIncrease, 0.05, 0.10, False),  # was rolled: compounding
    (FlatHPIncrease, 3, 8, True),
    (PercentHPIncrease, 0.05, 0.10, False),
    (XPIncrease, None, None, False),
    (LuckyIncrease, 3, 5, False),
    (FlatAttacCountIncrease, 1, 1, False),
    # Helixbound
    (FlatMANAIncrease, 3, 6, False),  # was 5, 10, True
    (PercentMANAIncrease, 0.05, 0.10, False),
    (ManaRegenIncrease, 1, 1, False),
    # Whisperbound
    (FlatStaminaIncrease, 5, 10, True),
    (PercentStaminaIncrease, 0.05, 0.10, False),
    (SprintCostDecrease, 1, 1, False),
    # Gorebound
    (MassGainIncrease, 1, 3, True),
    (InstantMassIncrease, 5, 10, True),
    (MassArmorIncrease, 1, 1, False),
]


class AffixManager:
    def __init__(self, engine) -> None:
        self.engine = engine
        self.affixes = []
        self.message_log = MessageLog()

    def gain_affix(self, affix: Affix):
        self.affixes.append(affix)
        self.message_log.add_message(text=affix.AFFIX_NAME)
        self.derive_affixes()

    def derive_affixes(self):
        for affix in self.affixes:
            if not affix.is_set:
                affix.apply_affix(self.engine)

    # --- rolling ---

    def make(self, row, level: Optional[int] = None) -> Affix:
        """One affix from an AFFIX_TABLE row, rolled for this player level."""
        cls, low, high, scales = row
        if level is None:
            level = self.engine.player.level.current_level
        if low is None:
            value = None
        elif isinstance(low, float):
            value = random.uniform(low, high)
        else:
            value = random.randint(low, high)
            if scales:
                value = stats.scaled(value, level)
        kind = self.engine.player.fighter.main_stat_kind
        return cls(value, stats.STAT_NAMES.get(kind, "Main stat"))

    def pools(self, exclude=frozenset()):
        """(everyone, this class) rows of AFFIX_TABLE."""
        player_class = self.engine.player.player_class
        rows = [row for row in AFFIX_TABLE if row[0] not in exclude]
        general = [row for row in rows if row[0].CLASS_LOCK == PlayerClass.GENERIC]
        own = [row for row in rows if row[0].CLASS_LOCK == player_class]
        return general, own

    def roll(self, level: Optional[int] = None, exclude=frozenset()) -> Affix:
        """One random affix: from the class pool (CLASS_POOL_CHANCE) or the
        general pool, then by rarity weight inside that pool."""
        general, own = self.pools(exclude)
        use_own = own and (not general or random.random() < stats.CLASS_POOL_CHANCE)
        pool = own if use_own else general
        weights = [stats.RARITY_WEIGHTS[row[0].AFFIX_COLOR.name] for row in pool]
        return self.make(random.choices(pool, weights=weights)[0], level)

    def roll_choices(self, level: Optional[int] = None, count: int = 0) -> List[Affix]:
        """Different affixes to pick one from on level-up."""
        choices: List[Affix] = []
        for _ in range(count or stats.AFFIX_CHOICES):
            taken = {type(affix) for affix in choices}
            if not any(self.pools(taken)):
                break
            choices.append(self.roll(level, exclude=taken))
        return choices

    def rand_affix(self):
        return self.roll()

    def get_affix_dir(self):
        """One of every affix that can be rolled, for the cheat menu."""
        return [self.make(row) for row in AFFIX_TABLE]

    def get_sepcific_affix(self, index: int):
        return self.get_affix_dir()[index]
