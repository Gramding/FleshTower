from components.ai import HostileEnemy, HostileCaster, Vendor
from components.fighter import Fighter
from components.inventory import Inventory
from components import consumable, equippable
from components.equipment import Equipment
from entity import Actor, Item
from components.level import Level
from components.spells import SpellBook
from components.effects import *

player = Actor(
    char="@",
    color=(255, 255, 255),
    name="Player",
    ai_cls=HostileEnemy,
    equipment=Equipment(),
    fighter=Fighter(hp=30, base_defense=1, base_power=3),
    inventory=Inventory(capacity=26),
    level=Level(level_up_base=100),
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
    fighter=Fighter(hp=3, base_defense=0, base_power=1),
    inventory=Inventory(capacity=0),
    level=Level(xp_given=5),
    spellbook=SpellBook(0),
    logbook=LogBook(),
    effect=DefautlEffect(),
)

goblin = Actor(
    char="g",
    color=(0, 128, 0),
    name="Goblin",
    ai_cls=HostileEnemy,
    equipment=Equipment(),
    fighter=Fighter(hp=6, base_defense=0, base_power=2),
    inventory=Inventory(capacity=0),
    level=Level(xp_given=20),
    spellbook=SpellBook(0),
    logbook=LogBook(),
    effect=DefautlEffect(),
)

orc = Actor(
    char="o",
    color=(63, 127, 63),
    name="Orc",
    ai_cls=HostileEnemy,
    equipment=Equipment(),
    fighter=Fighter(hp=10, base_defense=0, base_power=3),
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
    fighter=Fighter(hp=16, base_defense=1, base_power=4),
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
    fighter=Fighter(hp=14, base_defense=3, base_power=2),
    inventory=Inventory(capacity=0),
    level=Level(xp_given=100),
    spellbook=SpellBook(0),
    logbook=LogBook(),
    # TODO Special effect for consumption
    # should in this case be a negative one
    # at 25 or so consumed, player turns undead
    effect=DefautlEffect(),
)

flesh_golem = Actor(
    char="G",
    color=(128, 127, 0),
    name="Flesh Golem",
    ai_cls=HostileEnemy,
    equipment=Equipment(),
    fighter=Fighter(hp=40, base_defense=4, base_power=5),
    inventory=Inventory(capacity=0),
    level=Level(xp_given=250),
    spellbook=SpellBook(0),
    logbook=LogBook(),
    # TODO special effect for consumption
    # should be positive effect at 5 consumed
    # effect player "gains" additional arm and does additional attack in meele range
    # player looses mage and gains double hp
    effect=DefautlEffect(),
)

lvl5_boss = Actor(
    char="m",
    color=(0, 127, 50),
    name="Weak Mage",
    ai_cls=HostileCaster,
    equipment=Equipment(),
    fighter=Fighter(hp=20, base_defense=0, base_power=4),
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
    fighter=Fighter(hp=20, base_defense=0, base_power=4),
    inventory=Inventory(capacity=5),
    level=Level(xp_given=10),
    spellbook=SpellBook(0),
    logbook=LogBook(),
    effect=Lvl5BossEffect(),
)

health_potion = Item(
    char="!",
    color=(127, 0, 255),
    name="Health Potion",
    consumable=consumable.HealingConsumable(amount=4),
    effect=HealthEffect(),
    price=10,
)

large_health_potion = Item(
    char="!",
    color=(255, 0, 127),
    name="Large Health Potion",
    consumable=consumable.HealingConsumable(amount=10),
    effect=HealthEffect(),
    price=50,
)

mana_potion = Item(
    char="!",
    color=(0, 0, 255),
    name="Mana Potion",
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
