import math
import random
import copy
from components.settings import PlayerClass
# To enhance add class wich derives from Affix and remember to also
# add new class to the AFFIX_DIR


class Affix:
    AFFIX_NAME = ""
    CLASS_LOCK = PlayerClass.GENERIC

    def __init__(self) -> None:
        self.is_set = False
        pass

    def apply_affix(self, player):
        raise NotImplementedError()


class FlatIncrease(Affix):
    def __init__(self, flatValue: int, AFFIX_NAME: str) -> None:
        self.AFFIX_NAME = f"Flat {flatValue} {AFFIX_NAME}"
        self.flatValue = flatValue
        super().__init__()

    def apply_affix(self, player):
        self.is_set = True


class PercentIncrease(Affix):
    def __init__(self, percentValue: float, AFFIX_NAME: str) -> None:
        self.AFFIX_NAME = f"{percentValue:.0%} {AFFIX_NAME}"
        self.percentValue = percentValue
        super().__init__()

    def apply_affix(self, player):
        self.is_set = True


class PercentHPIncrease(PercentIncrease):
    AFFIX_NAME = "HP increase"

    def __init__(self, percentValue: float) -> None:
        super().__init__(percentValue, self.AFFIX_NAME)

    def apply_affix(self, player):
        increase = player.fighter.max_hp + math.ceil(
            player.fighter.max_hp * self.percentValue
        )

        player.fighter.max_hp = increase
        self.is_set = True


class PercentMANAIncrease(PercentIncrease):
    AFFIX_NAME = "Mana increase"
    CLASS_LOCK = PlayerClass.MAGE

    def __init__(self, percentValue: float) -> None:
        super().__init__(percentValue, self.AFFIX_NAME)

    def apply_affix(self, player):
        increase = player.fighter.max_mana + math.ceil(
            player.fighter.max_mana * self.percentValue
        )
        player.fighter.max_mana = increase
        super().apply_affix(player)


class PercentMeeleIncrease(PercentIncrease):
    AFFIX_NAME = "Meele increase"

    def __init__(self, percentValue: float) -> None:
        super().__init__(percentValue, self.AFFIX_NAME)

    def apply_affix(self, player):
        increase = player.fighter.power + math.ceil(
            player.fighter.power * self.percentValue
        )
        player.fighter.power = increase
        super().apply_affix(player)


class PercentDamageReductionIncrease(PercentIncrease):
    AFFIX_NAME = "Damage Reduction increase"

    def __init__(self, percentValue: float) -> None:
        super().__init__(percentValue, self.AFFIX_NAME)

    def apply_affix(self, player):
        increase = player.fighter.defense + math.ceil(
            player.fighter.defense * self.percentValue
        )
        player.fighter.defense = increase

        super().apply_affix(player)


class PercentStaminaIncrease(PercentIncrease):
    AFFIX_NAME = "Stamina increase"
    CLASS_LOCK = PlayerClass.ROUGE

    def __init__(self, percentValue: float) -> None:
        super().__init__(percentValue, self.AFFIX_NAME)

    def apply_affix(self, player):
        increase = player.fighter.max_stamina + math.ceil(
            player.fighter.max_stamina * self.percentValue
        )
        player.fighter.max_stamina = increase

        super().apply_affix(player)


class FlatHPIncrease(FlatIncrease):
    AFFIX_NAME = "HP increase"

    def __init__(self, flatValue: int) -> None:
        super().__init__(flatValue, self.AFFIX_NAME)

    def apply_affix(self, player):
        player.fighter.max_hp += self.flatValue
        super().apply_affix(player)


class FlatMANAIncrease(FlatIncrease):
    AFFIX_NAME = "Mana increase"
    CLASS_LOCK = PlayerClass.MAGE

    def __init__(self, flatValue: int) -> None:
        super().__init__(flatValue, self.AFFIX_NAME)

    def apply_affix(self, player):
        player.fighter.max_mana += self.flatValue
        super().apply_affix(player)


class FlatMeeleIncrease(FlatIncrease):
    AFFIX_NAME = "Meele increase"

    def __init__(self, flatValue: int) -> None:
        super().__init__(flatValue, self.AFFIX_NAME)

    def apply_affix(self, player):
        player.fighter.power += self.flatValue
        super().apply_affix(player)


class FlatDamageReductionIncrease(FlatIncrease):
    AFFIX_NAME = "Damage reduction increase"

    def __init__(self, flatValue: int) -> None:
        super().__init__(flatValue, self.AFFIX_NAME)

    def apply_affix(self, player):
        player.fighter.defense += self.flatValue
        super().apply_affix(player)


class FlatStaminaIncrease(FlatIncrease):
    AFFIX_NAME = "Stamina increase"
    CLASS_LOCK = PlayerClass.ROUGE

    def __init__(self, flatValue: int) -> None:
        super().__init__(flatValue, self.AFFIX_NAME)

    def apply_affix(self, player):
        player.fighter.max_stamina += self.flatValue
        super().apply_affix(player)


class AffixManager:
    def __init__(self, player) -> None:
        self.player = player
        self.affixes = []

    def gain_affix(self, affix: Affix):
        self.affixes.append(affix)
        self.derive_affixes()

    def derive_affixes(self):
        for affix in self.affixes:
            if not affix.is_set:
                affix.apply_affix(self.player)

    def rand_affix(self):
        AFFIX_DIR = self.get_affix_dir()
        while True:
            current_affix = AFFIX_DIR[random.randint(0, len(AFFIX_DIR) - 1)]
            if current_affix.CLASS_LOCK == PlayerClass.GENERIC:
                return current_affix
            elif current_affix.CLASS_LOCK == self.player.player_class:
                return copy.deepcopy(current_affix)

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
        ]

    def get_sepcific_affix(self, index: int):
        return self.get_affix_dir()[index]
