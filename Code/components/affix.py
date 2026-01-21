import math
import random
from color import AffixColor
from components.settings import PlayerClass

# To enhance add cl
# ass wich derives from Affix and remember to also
# add new class to the AFFIX_DIR


class Affix():
    AFFIX_NAME = ""
    CLASS_LOCK = PlayerClass.GENERIC
    AFFIX_COLOR = AffixColor.COMMON

    def __init__(self) -> None:
        self.is_set = False
        pass

    def apply_affix(self, engine):
        self.is_set = True


class FlatIncrease(Affix):
    def __init__(self, flatValue: int, AFFIX_NAME: str) -> None:
        self.AFFIX_NAME = f"Flat {flatValue} {AFFIX_NAME}"
        self.flatValue = flatValue
        super().__init__()

    def apply_affix(self, engine):
        super().apply_affix(engine)


class PercentIncrease(Affix):
    def __init__(self, percentValue: float, AFFIX_NAME: str) -> None:
        self.AFFIX_NAME = f"{percentValue:.0%} {AFFIX_NAME}"
        self.percentValue = percentValue
        super().__init__()

    def apply_affix(self, engine):
        super().apply_affix(engine)


class PercentHPIncrease(PercentIncrease):
    AFFIX_NAME = "HP increase"

    def __init__(self, percentValue: float) -> None:
        super().__init__(percentValue, self.AFFIX_NAME)

    def apply_affix(self, engine):
        increase = engine.player.fighter.max_hp + math.ceil(
            engine.player.fighter.max_hp * self.percentValue
        )

        engine.player.fighter.max_hp = increase
        super().apply_affix(engine)


class PercentMANAIncrease(PercentIncrease):
    AFFIX_NAME = "Mana increase"
    CLASS_LOCK = PlayerClass.MAGE

    def __init__(self, percentValue: float) -> None:
        super().__init__(percentValue, self.AFFIX_NAME)

    def apply_affix(self, engine):
        increase = engine.player.fighter.max_mana + math.ceil(
            engine.player.fighter.max_mana * self.percentValue
        )
        engine.player.fighter.max_mana = increase
        super().apply_affix(engine)


class PercentMeeleIncrease(PercentIncrease):
    AFFIX_NAME = "Meele increase"

    def __init__(self, percentValue: float) -> None:
        super().__init__(percentValue, self.AFFIX_NAME)

    def apply_affix(self, engine):
        increase = engine.player.fighter.power + math.ceil(
            engine.player.fighter.power * self.percentValue
        )
        engine.player.fighter.power = increase
        super().apply_affix(engine)


class PercentDamageReductionIncrease(PercentIncrease):
    AFFIX_NAME = "Damage Reduction increase"

    def __init__(self, percentValue: float) -> None:
        super().__init__(percentValue, self.AFFIX_NAME)

    def apply_affix(self, engine):
        increase = engine.player.fighter.defense + math.ceil(
            engine.player.fighter.defense * self.percentValue
        )
        engine.player.fighter.defense = increase

        super().apply_affix(engine)


class PercentStaminaIncrease(PercentIncrease):
    AFFIX_NAME = "Stamina increase"
    CLASS_LOCK = PlayerClass.ROUGE

    def __init__(self, percentValue: float) -> None:
        super().__init__(percentValue, self.AFFIX_NAME)

    def apply_affix(self, engine):
        increase = engine.player.fighter.max_stamina + math.ceil(
            engine.player.fighter.max_stamina * self.percentValue
        )
        engine.player.fighter.max_stamina = increase

        super().apply_affix(engine)


class FlatHPIncrease(FlatIncrease):
    AFFIX_NAME = "HP increase"

    def __init__(self, flatValue: int) -> None:
        super().__init__(flatValue, self.AFFIX_NAME)

    def apply_affix(self, engine):
        engine.player.fighter.max_hp += self.flatValue
        super().apply_affix(engine)


class FlatMANAIncrease(FlatIncrease):
    AFFIX_NAME = "Mana increase"
    CLASS_LOCK = PlayerClass.MAGE

    def __init__(self, flatValue: int) -> None:
        super().__init__(flatValue, self.AFFIX_NAME)

    def apply_affix(self, engine):
        engine.player.fighter.max_mana += self.flatValue
        super().apply_affix(engine)


class FlatMeeleIncrease(FlatIncrease):
    AFFIX_NAME = "Meele increase"
    AFFIX_COLOR = AffixColor.RARE

    def __init__(self, flatValue: int) -> None:
        super().__init__(flatValue, self.AFFIX_NAME)

    def apply_affix(self, engine):
        engine.player.fighter.power += self.flatValue
        super().apply_affix(engine)


class FlatDamageReductionIncrease(FlatIncrease):
    AFFIX_NAME = "Damage reduction increase"

    def __init__(self, flatValue: int) -> None:
        super().__init__(flatValue, self.AFFIX_NAME)

    def apply_affix(self, engine):
        engine.player.fighter.defense += self.flatValue
        super().apply_affix(engine)


class FlatStaminaIncrease(FlatIncrease):
    AFFIX_NAME = "Stamina increase"
    CLASS_LOCK = PlayerClass.ROUGE

    def __init__(self, flatValue: int) -> None:
        super().__init__(flatValue, self.AFFIX_NAME)

    def apply_affix(self, engine):
        engine.player.fighter.max_stamina += self.flatValue
        super().apply_affix(engine)


class FlatAttacCountIncrease(FlatIncrease):
    AFFIX_NAME = "Attack count increase"
    AFFIX_COLOR = AffixColor.LEGENDARY

    def __init__(self, flatValue: int) -> None:
        super().__init__(flatValue, self.AFFIX_NAME)

    def apply_affix(self, engine):
        engine.player.fighter.attack_count += self.flatValue
        super().apply_affix(engine)


class XPIncrease(Affix):
    AFFIX_NAME = "XP Increase"
    AFFIX_COLOR = AffixColor.UNCOMMON

    def __init__(self) -> None:
        super().__init__()

    def apply_affix(self, engine):
        engine.player.level.add_xp(
            random.randint(
                int(engine.player.level.xp_to_next_level / 2),
                int(engine.player.level.xp_to_next_level * 2),
            )
        )

        super().apply_affix(engine)

class LuckyIncrease(Affix):
    AFFIX_NAME = "Lucky"
    AFFIX_COLOR = AffixColor.LEGENDARY

    def __init__(self,luckyAmount:int) -> None:
        self.lukyAmount =luckyAmount
        super().__init__()

    def apply_affix(self, engine,):
        super().apply_affix(engine)
        for i in range(self.lukyAmount):
            new_affix = engine.affixManager.rand_affix()
            if not isinstance(new_affix,LuckyIncrease):
                engine.affixManager.gain_affix(new_affix)
                



class AffixManager:
    def __init__(self, engine) -> None:
        self.engine = engine
        self.affixes = []

    def gain_affix(self, affix: Affix):
        self.affixes.append(affix)
        self.derive_affixes()

    def derive_affixes(self):
        for affix in self.affixes:
            if not affix.is_set:
                affix.apply_affix(self.engine)

    def rand_affix(self):
        AFFIX_DIR = self.get_affix_dir()
        while True:
            current_affix = AFFIX_DIR[random.randint(0, len(AFFIX_DIR) - 1)]
            if current_affix.CLASS_LOCK == PlayerClass.GENERIC:
                return current_affix
            elif current_affix.CLASS_LOCK == self.engine.player.player_class:
                return current_affix

    def get_affix_dir(self):
        return [
            PercentHPIncrease(random.uniform(0.01, 0.1)),
            PercentMANAIncrease(random.uniform(0.01, 0.1)),
            PercentMeeleIncrease(random.uniform(0.01, 0.1)),
            PercentDamageReductionIncrease(random.uniform(0.01, 0.1)),
            PercentStaminaIncrease(random.uniform(0.01, 0.1)),
            FlatHPIncrease(random.randint(1, 5)),
            FlatMANAIncrease(random.randint(1, 5)),
            FlatMeeleIncrease(random.randint(1, 5)),
            FlatDamageReductionIncrease(random.randint(1, 5)),
            FlatStaminaIncrease(random.randint(1, 5)),
            FlatAttacCountIncrease(1),
            XPIncrease(),
            LuckyIncrease(random.randint(3, 5)),
        ]

    def get_sepcific_affix(self, index: int):
        return self.get_affix_dir()[index]
