import math
import random
import copy
# To enhance add class wich derives from Affix and remember to also
# add new class to the AFFIX_DIR


class Affix:
    AFFIX_NAME = ""

    def __init__(self) -> None:
        self.is_set = False
        pass

    def apply_affix(self, player):
        raise NotImplementedError()


class PercentIncrease(Affix):
    def __init__(self, percentValue: float, AFFIX_NAME: str) -> None:
        self.AFFIX_NAME = f"{percentValue:.0%} {AFFIX_NAME}"
        self.percentValue = percentValue
        super().__init__()

    def apply_affix(self, player):
        raise NotImplementedError()


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

    def __init__(self, percentValue: float) -> None:
        super().__init__(percentValue, self.AFFIX_NAME)

    def apply_affix(self, player):
        increase = player.fighter.max_mana + math.ceil(
            player.fighter.max_mana * self.percentValue
        )
        player.fighter.max_mana = increase

        self.is_set = True


class PercentMeeleIncrease(PercentIncrease):
    AFFIX_NAME = "Meele increase"

    def __init__(self, percentValue: float) -> None:
        super().__init__(percentValue, self.AFFIX_NAME)

    def apply_affix(self, player):
        increase = player.fighter.power + math.ceil(
            player.fighter.power * self.percentValue
        )
        player.fighter.power = increase

        self.is_set = True


class PercentDamageReductionIncrease(PercentIncrease):
    AFFIX_NAME = "Damage Reduction increase"

    def __init__(self, percentValue: float) -> None:
        super().__init__(percentValue, self.AFFIX_NAME)

    def apply_affix(self, player):
        increase = player.fighter.defense + math.ceil(
            player.fighter.defense * self.percentValue
        )
        player.fighter.defense = increase

        self.is_set = True


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
        return copy.deepcopy(AFFIX_DIR[random.randint(0, len(AFFIX_DIR) - 1)])

    def get_affix_dir(self):
        return [
            PercentHPIncrease(random.uniform(0.01, 0.1)),
            PercentMANAIncrease(random.uniform(0.01, 0.1)),
            PercentMeeleIncrease(random.uniform(0.01, 0.1)),
            PercentDamageReductionIncrease(random.uniform(0.01, 0.1)),
        ]
