from __future__ import annotations

from typing import TYPE_CHECKING

from components.base_component import BaseComponent
from equipment_types import EquipmentType

if TYPE_CHECKING:
    from entity import Item


class Equippable(BaseComponent):
    parent: Item

    def __init__(
        self,
        equipment_type: EquipmentType,
        power_bonus: int = 0,
        defense_bonus: int = 0,
        stat_bonus: dict = {},
    ):
        self.equipment_type = equipment_type
        self.power_bonus = power_bonus
        self.defense_bonus = defense_bonus
        self.stat_bonus = stat_bonus
        self.is_applied = False


class Dagger(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.WEAPON, power_bonus=2)


class Sword(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.WEAPON, power_bonus=4)


class BonegrinderMaul(Equippable):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.WEAPON,
            power_bonus=4,
            stat_bonus={"TM": 2, "NS": 0, "FI": 1, "CD": 0, "PE": 0, "VI": 0},
        )


class Sinewcleaver(Equippable):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.WEAPON,
            power_bonus=3,
            stat_bonus={"TM": 1, "NS": 2, "FI": 0, "CD": 0, "PE": 0, "VI": 0},
        )


class NeuralRazor(Equippable):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.WEAPON,
            power_bonus=2,
            stat_bonus={"TM": 0, "NS": 3, "FI": 0, "CD": 1, "PE": 0, "VI": 0},
        )


class SpineTalon(Equippable):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.WEAPON,
            power_bonus=3,
            stat_bonus={"TM": 1, "NS": 1, "FI": 0, "CD": 0, "PE": 1, "VI": 0},
        )


class MarrowSaw(Equippable):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.WEAPON,
            power_bonus=6,
            stat_bonus={"TM": 2, "NS": 0, "FI": 1, "CD": 0, "PE": 0, "VI": 0},
        )


class VisceraBlade(Equippable):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.WEAPON,
            power_bonus=4,
            stat_bonus={"TM": 1, "NS": 1, "FI": 1, "CD": 0, "PE": 0, "VI": 0},
        )


class GristleHook(Equippable):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.WEAPON,
            power_bonus=3,
            stat_bonus={"TM": 0, "NS": 2, "FI": 0, "CD": 0, "PE": 1, "VI": 0},
        )


class PhageFang(Equippable):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.WEAPON,
            power_bonus=4,
            stat_bonus={"TM": 1, "NS": 0, "FI": 0, "CD": 2, "PE": 0, "VI": 0},
        )


class KnottedMace(Equippable):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.WEAPON,
            power_bonus=5,
            stat_bonus={"TM": 2, "NS": 0, "FI": 1, "CD": 0, "PE": 0, "VI": 0},
        )


class ThrallReaver(Equippable):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.WEAPON,
            power_bonus=7,
            stat_bonus={"TM": 3, "NS": 0, "FI": 2, "CD": 0, "PE": 1, "VI": 0},
        )


class LeatherArmor(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.ARMOR, defense_bonus=1)


class ChainMail(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.ARMOR, defense_bonus=3)


# =========================
# HEAD ITEMS
# =========================
class CrimsonSkullcap(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.HEAD, defense_bonus=1)


class FlayedHelm(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.HEAD, defense_bonus=2)


class OozeCrownedCap(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.HEAD, stat_bonus={"FI": 1})


class BoneplateHood(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.HEAD, defense_bonus=1)


class PulsingCranium(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.HEAD, stat_bonus={"TM": 1})


class VeinwovenCirclet(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.HEAD, stat_bonus={"NS": 1})


class TumorCrownedHelm(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.HEAD, defense_bonus=2)


class ShreddedFaceguard(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.HEAD, stat_bonus={"CD": 1})


class Sinewcap(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.HEAD, defense_bonus=1)


class MarrowVisage(Equippable):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.HEAD, stat_bonus={"FI": 1, "TM": 1}
        )


# =========================
# EYES ITEMS
# =========================
class BlindeyeLenses(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.EYES, stat_bonus={"NS": 1})


class ThirdOrb(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.EYES, stat_bonus={"CD": 1})


class GoreSightGoggles(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.EYES, stat_bonus={"FI": 1})


class HemogazeLens(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.EYES, stat_bonus={"TM": 1})


class OcularTumor(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.EYES, stat_bonus={"PE": 1})


class VeinboundSpectacles(Equippable):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.EYES, stat_bonus={"NS": 1, "CD": 1}
        )


class CorruptedIris(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.EYES, stat_bonus={"FI": 1})


class EyeOfTheWyrm(Equippable):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.EYES, stat_bonus={"TM": 1, "FI": 1}
        )


class PustularEyeband(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.EYES, stat_bonus={"CD": 1})


class BloodstareMonocle(Equippable):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.EYES, stat_bonus={"NS": 1, "PE": 1}
        )


# =========================
# NECKLACE ITEMS
# =========================
class Throatlace(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.NECKLACE, stat_bonus={"FI": 1})


class HumeralChain(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.NECKLACE, stat_bonus={"TM": 1})


class TumorAmulet(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.NECKLACE, stat_bonus={"CD": 1})


class HeartstringPendant(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.NECKLACE, stat_bonus={"NS": 1})


class SinewChoker(Equippable):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.NECKLACE, stat_bonus={"FI": 1, "TM": 1}
        )


class PulsingCollar(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.NECKLACE, stat_bonus={"PE": 1})


class OssifiedTorque(Equippable):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.NECKLACE, stat_bonus={"CD": 1, "FI": 1}
        )


class VeinloopNecklace(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.NECKLACE, stat_bonus={"NS": 1})


class RibBoundMedallion(Equippable):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.NECKLACE, stat_bonus={"TM": 1, "PE": 1}
        )


class CarotidChain(Equippable):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.NECKLACE, stat_bonus={"FI": 1, "CD": 1}
        )


# =========================
# CLOAK ITEMS
# =========================
class ShreddedShroud(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.CLOAK, defense_bonus=1)


class VeinMantle(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.CLOAK, defense_bonus=2)


class CysticCape(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.CLOAK, stat_bonus={"FI": 1})


class RottingWing(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.CLOAK, defense_bonus=1)


class SkinfoldMantle(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.CLOAK, stat_bonus={"TM": 1})


class IchorousDrape(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.CLOAK, stat_bonus={"NS": 1})


class TendrilCloak(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.CLOAK, stat_bonus={"CD": 1})


class MarrowVeil(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.CLOAK, defense_bonus=2)


class FleshTatteredRobe(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.CLOAK, defense_bonus=1)


class OozingPall(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.CLOAK, stat_bonus={"PE": 1})


# =========================
# WRIST ITEMS
# =========================
class GristleBracer(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.WRIST, stat_bonus={"TM": 1})


class BoneCuffs(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.WRIST, defense_bonus=1)


class ThrobbingBand(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.WRIST, stat_bonus={"FI": 1})


class SinewWrap(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.WRIST, stat_bonus={"NS": 1})


class TumorousWristguard(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.WRIST, defense_bonus=1)


class MarrowCuff(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.WRIST, stat_bonus={"CD": 1})


class VeinlaceWristband(Equippable):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.WRIST, stat_bonus={"TM": 1, "FI": 1}
        )


class PustuleBracelet(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.WRIST, stat_bonus={"PE": 1})


class OssifiedArmlet(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.WRIST, defense_bonus=2)


class Bloodring(Equippable):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.WRIST, stat_bonus={"NS": 1, "CD": 1}
        )


# =========================
# BELT ITEMS
# =========================
class GutsBelt(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.BELT, stat_bonus={"FI": 1})


class RibBinder(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.BELT, defense_bonus=1)


class VisceralCinch(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.BELT, stat_bonus={"TM": 1})


class TendonGirdle(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.BELT, stat_bonus={"NS": 1})


class Fleshbinder(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.BELT, defense_bonus=1)


class VeinloopSash(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.BELT, stat_bonus={"CD": 1})


class TumorLacedStrap(Equippable):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.BELT, stat_bonus={"FI": 1, "PE": 1}
        )


class BoneClaspBelt(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.BELT, defense_bonus=2)


class Marrowstrap(Equippable):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.BELT, stat_bonus={"TM": 1, "NS": 1}
        )


class Sinewbelt(Equippable):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.BELT, stat_bonus={"CD": 1, "FI": 1}
        )


# =========================
# LEGS ITEMS
# =========================
class ShreddedGreaves(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.LEGS, defense_bonus=1)


class VeinWrappedLeggings(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.LEGS, defense_bonus=2)


class BoneSplicedTrousers(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.LEGS, defense_bonus=1)


class TendonLacedPants(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.LEGS, stat_bonus={"TM": 1})


class MarrowStitchedLegwraps(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.LEGS, defense_bonus=2)


class FleshboundBreeches(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.LEGS, stat_bonus={"FI": 1})


class SinewweaveLeggings(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.LEGS, stat_bonus={"NS": 1})


class TumorousLegplates(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.LEGS, defense_bonus=2)


class PulsingCalfwraps(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.LEGS, stat_bonus={"PE": 1})


class SkinWrappedLegguards(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.LEGS, defense_bonus=1)


class Ring(Equippable):
    def __init__(
        self,
        equipment_type,
        stat_bonus: dict = {"TM": 0, "NS": 0, "FI": 0, "CD": 0, "PE": 0, "VI": 0},
    ):
        super().__init__(
            equipment_type=equipment_type,
            stat_bonus=stat_bonus,
        )


class WierdRing(Ring):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.RING,
            stat_bonus={"CD": 1},
        )


class OssuaryLoop(Ring):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.RING,
            stat_bonus={"TM": 2, "FI": 1},
        )


class Veinbinder(Ring):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.RING,
            stat_bonus={"NS": 2, "FI": 1},
        )


class WeepingKnuckle(Ring):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.RING,
            stat_bonus={"FI": 1, "PE": 2},
        )


class PhageCirclet(Ring):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.RING,
            stat_bonus={"FI": 1, "CD": 2, "VI": 1},
        )


class Stitchband(Ring):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.RING,
            stat_bonus={"TM": 1, "NS": 1, "FI": 1},
        )


class MawsEmbrace(Ring):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.RING,
            stat_bonus={"TM": 2, "PE": 1, "VI": 1},
        )


class CarrionLoop(Ring):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.RING,
            stat_bonus={"FI": 2, "PE": 1},
        )


class ThrobbingHalo(Ring):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.RING,
            stat_bonus={"NS": 1, "CD": 1, "PE": 2},
        )


class TumorsPromise(Ring):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.RING,
            stat_bonus={"TM": 1, "FI": 2, "VI": 1},
        )


class KnottedVisceraBand(Ring):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.RING,
            stat_bonus={"TM": 1, "FI": 1, "CD": 1},
        )
