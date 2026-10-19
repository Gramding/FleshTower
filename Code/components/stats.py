"""Class rules and every number of the stat system, in one place for balancing.

Each class has one main stat. The player's stats are computed from it by
Fighter (components/fighter.py); monsters only use plain hp, power and armor.
"""
from components.settings import PlayerClass

STR, DEX, INT = "STR", "DEX", "INT"
STAT_NAMES = {STR: "Strength", DEX: "Dexterity", INT: "Intelligence"}

# hp: added to (or taken from) the player's base HP when the class is chosen
CLASSES = {
    PlayerClass.FIGHTER: dict(name="Gorebound", stat=STR, hp=10, resource="mass"),
    PlayerClass.ROUGE: dict(name="Whisperbound", stat=DEX, hp=0, resource="stamina"),
    PlayerClass.MAGE: dict(name="Helixbound", stat=INT, hp=-10, resource="mana"),
}
DEFAULT_CLASS = PlayerClass.ROUGE  # until a class corpse is eaten

LEVEL_UP_STAT = 1  # main stat gained every level

# --- Balance pass 1 (2026-10-19, after the playtest bot) ---------------------
# Every value changed in this pass says "was ..."; the new behaviours have a
# switch. Set a value back to its "was" to undo that part.
PLAYER_DIAGONALS = False  # tried True (Y U B N, settings.KEYBINDS): not fun
ENEMY_DIAGONAL_ATTACKS = False  # was True: enemies only hit orthogonally, like the player
HP_REGEN_TURNS = 10  # was 0 (off): 1 HP every N turns while no enemy is in view
# ------------------------------------------------------------------------------

# STR (Gorebound)
STR_DAMAGE = 2  # +1 melee damage per 2 STR
STR_MASS = 0  # was 2: +1 mass per corpse per STR_MASS STR (0 = STR gives none)
STR_MASS_SAFETY = 3  # -1% chance to lose mass when hit per 3 STR
MASS_LOSS_CHANCE = 10  # % chance to lose 1-2 mass when hit, minus mass level
MASS_ARMOR = 1  # armor per MASS_ARMOR_LEVELS mass levels
MASS_ARMOR_LEVELS = 2  # was 1

# DEX (Whisperbound)
DEX_DAMAGE = 2  # was 3: +1 melee damage per 2 DEX
DEX_DODGE = 3  # was 2: % dodge chance per DEX
DODGE_CAP = 40
DEX_STAMINA_REGEN = 10  # +1 stamina per step per 10 DEX (on top of 1)
BASE_STAMINA = 30
SPRINT_COST = 2
LUNGE_COST = 10  # extra stamina for attacking 2 tiles away
LUNGE_DAMAGE = 2  # was 1: damage multiplier of the lunge
STAMINA_REGEN_ON_WAIT = True  # was False: waiting also regains stamina

# INT (Helixbound)
INT_SPELL = 2  # +1 spell damage / healing per 2 INT
BASE_MANA = 15
INT_MANA = 1  # was 3: max mana per INT
STARTER_SPELL_COST = 5  # was 2: mana of Lightning Bolt I
MANA_REGEN_SLOWEST = 10  # turns per mana point at 0 INT
INT_MANA_REGEN = 3  # one turn faster per 3 INT
MANA_REGEN_FASTEST = 2

# armor: reduction = armor / (armor + ARMOR_K), so 10 armor halves damage.
# Every point helps a bit less and it never reaches 100%.
ARMOR_K = 15  # was 10
ARMOR_CAP = 0.8  # at most 80% of a hit is absorbed


def armor_reduction(armor: int) -> float:
    if armor <= 0:
        return 0.0
    return min(ARMOR_CAP, armor / (armor + ARMOR_K))


def class_info(player_class):
    return CLASSES.get(player_class)


def mana_regen_turns(intelligence: int) -> int:
    return max(MANA_REGEN_FASTEST, MANA_REGEN_SLOWEST - intelligence // INT_MANA_REGEN)


# --- affixes (components/affix.py has each affix's value range and rarity) ---
AFFIX_LEVEL_SCALING = 0.15  # flat values grow by 15% of their roll per level
AFFIX_CHOICES = 3  # affixes offered on level-up, pick one
CLASS_POOL_CHANCE = 0.5  # each offer: chance to come from the class pool
RARITY_WEIGHTS = {  # how often each rarity is picked inside a pool
    "COMMON": 50,
    "UNCOMMON": 30,
    "RARE": 15,
    "EPIC": 4,
    "LEGENDARY": 1,
}
SPRINT_COST_MIN = 1
LUNGE_DISCOUNT_FACTOR = 2  # the lunge gets twice the sprint discount


def scaled(value: float, level: int) -> int:
    """A flat affix roll at this player level."""
    return max(1, round(value * (1 + level * AFFIX_LEVEL_SCALING)))
