from engine import Engine

def zombie(engine: Engine):
    engine.player.fighter.hp += 3

def flayed_thrall(engine: Engine):
    engine.player.fighter.base_hp += 1