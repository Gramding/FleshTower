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
    ):
        self.equipment_type = equipment_type
        self.power_bonus = power_bonus
        self.defense_bonus = defense_bonus


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
        )


class Sinewcleaver(Equippable):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.WEAPON,
            power_bonus=3,
        )


class NeuralRazor(Equippable):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.WEAPON,
            power_bonus=2,
        )


class SpineTalon(Equippable):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.WEAPON,
            power_bonus=3,
        )


class MarrowSaw(Equippable):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.WEAPON,
            power_bonus=6,
        )


class VisceraBlade(Equippable):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.WEAPON,
            power_bonus=4,
        )


class GristleHook(Equippable):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.WEAPON,
            power_bonus=3,
        )


class PhageFang(Equippable):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.WEAPON,
            power_bonus=4,
        )


class KnottedMace(Equippable):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.WEAPON,
            power_bonus=5,
        )


class ThrallReaver(Equippable):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.WEAPON,
            power_bonus=7,
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
        super().__init__(equipment_type=EquipmentType.HEAD)


class BoneplateHood(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.HEAD, defense_bonus=1)


class PulsingCranium(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.HEAD)


class VeinwovenCirclet(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.HEAD)


class TumorCrownedHelm(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.HEAD, defense_bonus=2)


class ShreddedFaceguard(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.HEAD)


class Sinewcap(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.HEAD, defense_bonus=1)


class MarrowVisage(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.HEAD)


# =========================
# EYES ITEMS
# =========================
class BlindeyeLenses(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.EYES)


class ThirdOrb(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.EYES)


class GoreSightGoggles(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.EYES)


class HemogazeLens(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.EYES)


class OcularTumor(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.EYES)


class VeinboundSpectacles(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.EYES)


class CorruptedIris(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.EYES)


class EyeOfTheWyrm(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.EYES)


class PustularEyeband(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.EYES)


class BloodstareMonocle(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.EYES)


# =========================
# NECKLACE ITEMS
# =========================
class Throatlace(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.NECKLACE)


class HumeralChain(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.NECKLACE)


class TumorAmulet(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.NECKLACE)


class HeartstringPendant(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.NECKLACE)


class SinewChoker(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.NECKLACE)


class PulsingCollar(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.NECKLACE)


class OssifiedTorque(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.NECKLACE)


class VeinloopNecklace(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.NECKLACE)


class RibBoundMedallion(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.NECKLACE)


class CarotidChain(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.NECKLACE)


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
        super().__init__(equipment_type=EquipmentType.CLOAK)


class RottingWing(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.CLOAK, defense_bonus=1)


class SkinfoldMantle(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.CLOAK)


class IchorousDrape(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.CLOAK)


class TendrilCloak(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.CLOAK)


class MarrowVeil(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.CLOAK, defense_bonus=2)


class FleshTatteredRobe(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.CLOAK, defense_bonus=1)


class OozingPall(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.CLOAK)


# =========================
# WRIST ITEMS
# =========================
class GristleBracer(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.WRIST)


class BoneCuffs(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.WRIST, defense_bonus=1)


class ThrobbingBand(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.WRIST)


class SinewWrap(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.WRIST)


class TumorousWristguard(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.WRIST, defense_bonus=1)


class MarrowCuff(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.WRIST)


class VeinlaceWristband(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.WRIST)


class PustuleBracelet(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.WRIST)


class OssifiedArmlet(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.WRIST, defense_bonus=2)


class Bloodring(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.WRIST)


# =========================
# BELT ITEMS
# =========================
class GutsBelt(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.BELT)


class RibBinder(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.BELT, defense_bonus=1)


class VisceralCinch(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.BELT)


class TendonGirdle(Equippable):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.BELT,
        )


class Fleshbinder(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.BELT, defense_bonus=1)


class VeinloopSash(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.BELT)


class TumorLacedStrap(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.BELT)


class BoneClaspBelt(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.BELT, defense_bonus=2)


class Marrowstrap(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.BELT)


class Sinewbelt(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.BELT)


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
        super().__init__(equipment_type=EquipmentType.LEGS)


class MarrowStitchedLegwraps(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.LEGS, defense_bonus=2)


class FleshboundBreeches(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.LEGS)


class SinewweaveLeggings(Equippable):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.LEGS,
        )


class TumorousLegplates(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.LEGS, defense_bonus=2)


class PulsingCalfwraps(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.LEGS)


class SkinWrappedLegguards(Equippable):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.LEGS, defense_bonus=1)


class Ring(Equippable):
    def __init__(
        self,
        equipment_type,
    ):
        super().__init__(
            equipment_type=equipment_type,
        )


class WierdRing(Ring):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.RING,
        )


class OssuaryLoop(Ring):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.RING,
        )


class Veinbinder(Ring):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.RING,
        )


class WeepingKnuckle(Ring):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.RING,
        )


class PhageCirclet(Ring):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.RING,
        )


class Stitchband(Ring):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.RING,
        )


class MawsEmbrace(Ring):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.RING,
        )


class CarrionLoop(Ring):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.RING,
        )


class ThrobbingHalo(Ring):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.RING,
        )


class TumorsPromise(Ring):
    def __init__(self):
        super().__init__(
            equipment_type=EquipmentType.RING,
        )


class KnottedVisceraBand(Ring):
    def __init__(self):
        super().__init__(equipment_type=EquipmentType.RING)
