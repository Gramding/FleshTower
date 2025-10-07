from components.ai import HostileEnemy, HostileCaster, Vendor
from components.fighter import Fighter
from components.inventory import Inventory
from components import consumable, equippable
from components.equipment import Equipment
from entity import Actor, Item
from components.level import Level
from components.spells import SpellBook
from components.effects import *
from typing import Dict

player = Actor(
    char="@",
    color=(255, 255, 255),
    name="Player",
    ai_cls=HostileEnemy,
    equipment=Equipment(),
    fighter=Fighter(
        base_hp=30,
        base_defense=1,
        base_power=2,
        stats={"TM": 8, "NS": 8, "FI": 8, "CD": 8, "PE": 8, "VI": 8},
    ),
    inventory=Inventory(capacity=26),
    level=Level(level_up_base=0),
    spellbook=SpellBook(10),
    logbook=LogBook(),
    effect=None,
)

rat = Actor(
    char="r",
    color=(88, 57, 39),
    name="Rat",
    ai_cls=HostileEnemy,
    equipment=Equipment(),
    fighter=Fighter(
        base_hp=3,
        base_defense=0,
        base_power=1,
        stats={"TM": 8, "NS": 8, "FI": 8, "CD": 8, "PE": 8, "VI": 8},
    ),
    inventory=Inventory(capacity=0),
    level=Level(xp_given=5),
    spellbook=SpellBook(0),
    logbook=LogBook(),
    effect=DefaultEffect(),
)

goblin = Actor(
    char="g",
    color=(0, 128, 0),
    name="Goblin",
    ai_cls=HostileEnemy,
    equipment=Equipment(),
    fighter=Fighter(
        base_hp=6,
        base_defense=0,
        base_power=2,
        stats={"TM": 8, "NS": 8, "FI": 8, "CD": 8, "PE": 8, "VI": 8},
    ),
    inventory=Inventory(capacity=0),
    level=Level(xp_given=20),
    spellbook=SpellBook(0),
    logbook=LogBook(),
    effect=DefaultEffect(),
)

orc = Actor(
    char="o",
    color=(63, 127, 63),
    name="Orc",
    ai_cls=HostileEnemy,
    equipment=Equipment(),
    fighter=Fighter(
        base_hp=10,
        base_defense=0,
        base_power=3,
        stats={"TM": 8, "NS": 8, "FI": 8, "CD": 8, "PE": 8, "VI": 8},
    ),
    inventory=Inventory(capacity=0),
    level=Level(xp_given=35),
    spellbook=SpellBook(0),
    logbook=LogBook(),
    effect=OrcEffect(),
)
troll = Actor(
    char="t",
    color=(0, 127, 0),
    name="Troll",
    ai_cls=HostileEnemy,
    equipment=Equipment(),
    fighter=Fighter(
        base_hp=16,
        base_defense=1,
        base_power=4,
        stats={"TM": 8, "NS": 8, "FI": 8, "CD": 8, "PE": 8, "VI": 8},
    ),
    inventory=Inventory(capacity=0),
    level=Level(xp_given=100),
    spellbook=SpellBook(0),
    logbook=LogBook(),
    effect=TrollEffect(),
)

zombie = Actor(
    char="z",
    color=(52, 71, 54),
    name="Zombie",
    ai_cls=HostileEnemy,
    equipment=Equipment(),
    fighter=Fighter(
        base_hp=14,
        base_defense=3,
        base_power=2,
        stats={"TM": 8, "NS": 8, "FI": 8, "CD": 8, "PE": 8, "VI": 8},
    ),
    inventory=Inventory(capacity=0),
    level=Level(xp_given=100),
    spellbook=SpellBook(0),
    logbook=LogBook(),
    # TODO Special effect for consumption
    # should in this case be a negative one
    # at 25 or so consumed, player turns undead
    effect=DefaultEffect(),
)

flesh_golem = Actor(
    char="G",
    color=(128, 127, 0),
    name="Flesh Golem",
    ai_cls=HostileEnemy,
    equipment=Equipment(),
    fighter=Fighter(
        base_hp=40,
        base_defense=4,
        base_power=5,
        stats={"TM": 8, "NS": 8, "FI": 8, "CD": 8, "PE": 8, "VI": 8},
    ),
    inventory=Inventory(capacity=0),
    level=Level(xp_given=250),
    spellbook=SpellBook(0),
    logbook=LogBook(),
    effect=FleshGolemEffect(),
)

lvl5_boss = Actor(
    char="m",
    color=(0, 127, 50),
    name="Weak Mage",
    ai_cls=HostileCaster,
    equipment=Equipment(),
    fighter=Fighter(
        base_hp=20,
        base_defense=0,
        base_power=4,
        stats={"TM": 8, "NS": 8, "FI": 8, "CD": 8, "PE": 8, "VI": 8},
    ),
    inventory=Inventory(capacity=2),
    level=Level(xp_given=1000),
    spellbook=SpellBook(0),
    logbook=LogBook(),
    effect=Lvl5BossEffect(),
)

vendor = Actor(
    char="s",
    color=(179, 184, 55),
    name="Organ trader",
    ai_cls=Vendor,
    equipment=Equipment(),
    fighter=Fighter(
        base_hp=20,
        base_defense=0,
        base_power=4,
        stats={"TM": 8, "NS": 8, "FI": 8, "CD": 8, "PE": 8, "VI": 8},
    ),
    inventory=Inventory(capacity=5),
    level=Level(xp_given=10),
    spellbook=SpellBook(0),
    logbook=LogBook(),
    effect=DefaultEffect(),
)

flayed_thrall = Actor(
    char="t",
    color=(178, 34, 34),
    name="Flayed Thrall",
    ai_cls=HostileEnemy,
    equipment=Equipment(),
    fighter=Fighter(
        base_hp=10,
        base_defense=0,
        base_power=3,
        stats={"TM": 10, "NS": 7, "FI": 6, "CD": 6, "PE": 5, "VI": 4},
    ),
    inventory=Inventory(capacity=0),
    level=Level(xp_given=30),
    spellbook=SpellBook(0),
    logbook=LogBook(),
    effect=DefaultEffect(),
)


sinew_crawler = Actor(
    char="s",
    color=(139, 0, 0),
    name="Sinew Crawler",
    ai_cls=HostileEnemy,
    equipment=Equipment(),
    fighter=Fighter(
        base_hp=8,
        base_defense=1,
        base_power=4,
        stats={"TM": 9, "NS": 10, "FI": 7, "CD": 6, "PE": 6, "VI": 3},
    ),
    inventory=Inventory(capacity=0),
    level=Level(xp_given=25),
    spellbook=SpellBook(0),
    logbook=LogBook(),
    effect=DefaultEffect(),
)


howling_cyst = Actor(
    char="c",
    color=(255, 69, 0),
    name="Howling Cyst",
    ai_cls=HostileEnemy,
    equipment=Equipment(),
    fighter=Fighter(
        base_hp=12,
        base_defense=0,
        base_power=2,
        stats={"TM": 7, "NS": 5, "FI": 10, "CD": 9, "PE": 8, "VI": 6},
    ),
    inventory=Inventory(capacity=0),
    level=Level(xp_given=40),
    spellbook=SpellBook(1),
    logbook=LogBook(),
    effect=DefaultEffect(),
)


stitched_abomination = Actor(
    char="A",
    color=(105, 105, 105),
    name="Stitched Abomination",
    ai_cls=HostileEnemy,
    equipment=Equipment(),
    fighter=Fighter(
        base_hp=20,
        base_defense=2,
        base_power=5,
        stats={"TM": 12, "NS": 6, "FI": 11, "CD": 5, "PE": 4, "VI": 3},
    ),
    inventory=Inventory(capacity=0),
    level=Level(xp_given=60),
    spellbook=SpellBook(0),
    logbook=LogBook(),
    effect=DefaultEffect(),
)


vein_reaper = Actor(
    char="v",
    color=(220, 20, 60),
    name="Vein Reaper",
    ai_cls=HostileEnemy,
    equipment=Equipment(),
    fighter=Fighter(
        base_hp=14,
        base_defense=1,
        base_power=6,
        stats={"TM": 11, "NS": 9, "FI": 9, "CD": 7, "PE": 6, "VI": 5},
    ),
    inventory=Inventory(capacity=0),
    level=Level(xp_given=50),
    spellbook=SpellBook(0),
    logbook=LogBook(),
    effect=DefaultEffect(),
)


tumor_host = Actor(
    char="h",
    color=(186, 85, 211),
    name="Tumor Host",
    ai_cls=HostileEnemy,
    equipment=Equipment(),
    fighter=Fighter(
        base_hp=16,
        base_defense=0,
        base_power=3,
        stats={"TM": 8, "NS": 5, "FI": 12, "CD": 10, "PE": 7, "VI": 4},
    ),
    inventory=Inventory(capacity=0),
    level=Level(xp_given=55),
    spellbook=SpellBook(1),
    logbook=LogBook(),
    effect=DefaultEffect(),
)


marrow_drinker = Actor(
    char="m",
    color=(205, 133, 63),
    name="Marrow Drinker",
    ai_cls=HostileEnemy,
    equipment=Equipment(),
    fighter=Fighter(
        base_hp=18,
        base_defense=1,
        base_power=7,
        stats={"TM": 13, "NS": 8, "FI": 10, "CD": 6, "PE": 5, "VI": 4},
    ),
    inventory=Inventory(capacity=0),
    level=Level(xp_given=65),
    spellbook=SpellBook(0),
    logbook=LogBook(),
    effect=DefaultEffect(),
)


eye_screamer = Actor(
    char="e",
    color=(173, 216, 230),
    name="Eye Screamer",
    ai_cls=HostileEnemy,
    equipment=Equipment(),
    fighter=Fighter(
        base_hp=9,
        base_defense=0,
        base_power=2,
        stats={"TM": 6, "NS": 7, "FI": 7, "CD": 9, "PE": 11, "VI": 8},
    ),
    inventory=Inventory(capacity=0),
    level=Level(xp_given=30),
    spellbook=SpellBook(1),
    logbook=LogBook(),
    effect=DefaultEffect(),
)


gnashing_swarm = Actor(
    char="n",
    color=(255, 215, 0),
    name="Gnashing Swarm",
    ai_cls=HostileEnemy,
    equipment=Equipment(),
    fighter=Fighter(
        base_hp=12,
        base_defense=0,
        base_power=4,
        stats={"TM": 8, "NS": 11, "FI": 7, "CD": 5, "PE": 6, "VI": 4},
    ),
    inventory=Inventory(capacity=0),
    level=Level(xp_given=35),
    spellbook=SpellBook(0),
    logbook=LogBook(),
    effect=DefaultEffect(),
)


viscera_hound = Actor(
    char="H",
    color=(139, 0, 0),
    name="Viscera Hound",
    ai_cls=HostileEnemy,
    equipment=Equipment(),
    fighter=Fighter(
        base_hp=15,
        base_defense=1,
        base_power=5,
        stats={"TM": 12, "NS": 9, "FI": 9, "CD": 4, "PE": 6, "VI": 3},
    ),
    inventory=Inventory(capacity=0),
    level=Level(xp_given=45),
    spellbook=SpellBook(0),
    logbook=LogBook(),
    effect=DefaultEffect(),
)


health_potion = Item(
    char="!",
    color=(127, 0, 255),
    name="Health Potion",
    consumable=consumable.HealingConsumable(amount=15),
    effect=HealthEffect(),
    price=10,
)

large_health_potion = Item(
    char="!",
    color=(255, 0, 127),
    name="Large Health Potion",
    consumable=consumable.HealingConsumable(amount=30),
    effect=HealthEffect(),
    price=50,
)

mana_potion = Item(
    char="!",
    color=(0, 0, 255),
    name="Mutagen Potion",
    consumable=consumable.ManaConsumable(amount=10),
    effect=ManaEffect(),
    price=10,
)

lightning_scroll = Item(
    char="~",
    color=(255, 255, 0),
    name="Scroll of Lightning",
    consumable=consumable.LightningDamageConsumable(damage=20, maximum_range=5),
    effect=LightningEffect(),
    price=100,
)

confusion_scroll = Item(
    char="~",
    color=(207, 63, 255),
    name="Scroll of Confusion",
    consumable=consumable.ConfusionConsumable(number_of_turns=10),
    effect=ConfusionEffect(),
    price=100,
)

fireball_scroll = Item(
    char="~",
    color=(255, 0, 0),
    name="Scroll of Fireball",
    consumable=consumable.FireballDamageConsumable(damage=12, radius=3),
    effect=FireballEffect(),
    price=150,
)

dagger = Item(
    char="/",
    color=(0, 191, 255),
    name="Dagger",
    equippable=equippable.Dagger(),
    effect=DaggerEffect(),
    price=200,
)

sword = Item(
    char="/",
    color=(0, 191, 255),
    name="Sword",
    equippable=equippable.Sword(),
    effect=SwordEffect(),
    price=250,
)

bonegrinder_maul = Item(
    char="Ω",
    color=(139, 69, 19),
    name="Bonegrinder Maul",
    equippable=equippable.BonegrinderMaul(),
    effect=DefaultEffect(),
    price=300,
)

sinewcleaver = Item(
    char="╦",
    color=(165, 42, 42),
    name="Sinewcleaver",
    equippable=equippable.Sinewcleaver(),
    effect=DefaultEffect(),
    price=220,
)

neural_razor = Item(
    char="†",
    color=(178, 34, 34),
    name="Neural Razor",
    equippable=equippable.NeuralRazor(),
    effect=DefaultEffect(),
    price=200,
)

spine_talon = Item(
    char="»",
    color=(205, 92, 92),
    name="Spine Talon",
    equippable=equippable.SpineTalon(),
    effect=DefaultEffect(),
    price=240,
)

marrow_saw = Item(
    char="≡",
    color=(128, 0, 0),
    name="Marrow Saw",
    equippable=equippable.MarrowSaw(),
    effect=DefaultEffect(),
    price=400,
)

viscera_blade = Item(
    char="∫",
    color=(139, 0, 0),
    name="Viscera Blade",
    equippable=equippable.VisceraBlade(),
    effect=DefaultEffect(),
    price=260,
)

gristle_hook = Item(
    char="ʓ",
    color=(153, 50, 204),
    name="Gristle Hook",
    equippable=equippable.GristleHook(),
    effect=DefaultEffect(),
    price=230,
)

phage_fang = Item(
    char="λ",
    color=(255, 69, 0),
    name="Phage Fang",
    equippable=equippable.PhageFang(),
    effect=DefaultEffect(),
    price=280,
)

knotted_mace = Item(
    char="◉",
    color=(139, 69, 19),
    name="Knotted Mace",
    equippable=equippable.KnottedMace(),
    effect=DefaultEffect(),
    price=320,
)

thrall_reaver = Item(
    char="⚔",
    color=(178, 0, 0),
    name="Thrall Reaver",
    equippable=equippable.ThrallReaver(),
    effect=DefaultEffect(),
    price=450,
)


leather_armor = Item(
    char="[",
    color=(139, 69, 19),
    name="Leather Armor",
    equippable=equippable.LeatherArmor(),
    effect=LeatherArmorEffect(),
    price=200,
)

chain_mail = Item(
    char="[",
    color=(139, 69, 19),
    name="Chain Mail",
    equippable=equippable.ChainMail(),
    effect=ChainMailEffect(),
    price=300,
)

gorebound = Item(
    char="@",
    color=(255, 0, 0),
    name="- Gorebound -                  The Gorebound is an abomination that feeds to grow.          They do not wear armor. They become it.",
    effect=GoreboundEffect(),
    price=100,
)

helixbound = Item(
    char="@",
    color=(0, 0, 255),
    name="- Helixbound -                  The Helixbound is a vessel of unstable genetic recursion—a caster whose power is drawn not from words or will, but from rewriting their own biology.",
    effect=Lvl5BossEffect(),
    price=100,
)

wierd_ring = Item(
    char="o",
    color=(139, 69, 19),
    name="Wierd Ring",
    equippable=equippable.WierdRing(),
    effect=DefaultEffect(),
    price=300,
)

ossuary_loop = Item(
    char="o",
    color=(139, 69, 19),
    name="Ossuary Loop",
    equippable=equippable.OssuaryLoop(),
    effect=DefaultEffect(),
    price=300,
)

veinbinder = Item(
    char="o",
    color=(178, 34, 34),
    name="Veinbinder",
    equippable=equippable.Veinbinder(),
    effect=DefaultEffect(),
    price=350,
)

weeping_knuckle = Item(
    char="o",
    color=(105, 105, 105),
    name="Ring of the Weeping Knuckle",
    equippable=equippable.WeepingKnuckle(),
    effect=DefaultEffect(),
    price=280,
)

phage_circlet = Item(
    char="o",
    color=(165, 42, 42),
    name="Phage Circlet",
    equippable=equippable.PhageCirclet(),
    effect=DefaultEffect(),
    price=400,
)

stitchband = Item(
    char="o",
    color=(205, 92, 92),
    name="Stitchband",
    equippable=equippable.Stitchband(),
    effect=DefaultEffect(),
    price=320,
)

maws_embrace = Item(
    char="o",
    color=(139, 0, 0),
    name="The Maw’s Embrace",
    equippable=equippable.MawsEmbrace(),
    effect=DefaultEffect(),
    price=450,
)

carrion_loop = Item(
    char="o",
    color=(112, 128, 144),
    name="Carrion Loop",
    equippable=equippable.CarrionLoop(),
    effect=DefaultEffect(),
    price=250,
)

throbbing_halo = Item(
    char="o",
    color=(178, 0, 0),
    name="The Throbbing Halo",
    equippable=equippable.ThrobbingHalo(),
    effect=DefaultEffect(),
    price=380,
)

tumors_promise = Item(
    char="o",
    color=(222, 184, 135),
    name="Tumor’s Promise",
    equippable=equippable.TumorsPromise(),
    effect=DefaultEffect(),
    price=500,
)

knotted_viscera_band = Item(
    char="o",
    color=(139, 69, 19),
    name="Knotted Viscera Band",
    equippable=equippable.KnottedVisceraBand(),
    effect=DefaultEffect(),
    price=420,
)

