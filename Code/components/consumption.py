from engine import Engine


class ContinousConsumption:
    def __init__(self, engine: Engine, name: str) -> None:
        self.prefix = f"You're inner {name} grants you"
        self.postfix = "for this consumption"
        self.name = name
        self.engine = engine

    def activate(self):
        raise (NotImplementedError)

    def message(self, message):
        self.engine.message_log.add_message(message)


class ConsumptionFactory(ContinousConsumption):
    def __init__(self, engine, name) -> None:
        super().__init__(engine, name)

    def deriveClass(self, name) -> ContinousConsumption:
        match name:
            case "Zombie":
                return ZombieConsumption(self.engine, name)
            case "FlayedThrall":
                return FlayedTrallConsumption(self.engine, name)

        return ContinousConsumption(self.engine, "None")


# -------------------------------------------------------------------------- #


class ZombieConsumption(ContinousConsumption):
    def __init__(self, engine, name) -> None:
        super().__init__(engine, name)

    def activate(self):
        amount = 3
        self.engine.player.fighter.hp += amount
        self.message(f"{self.prefix} {amount} HP {self.postfix}")


class FlayedTrallConsumption(ContinousConsumption):
    def __init__(self, engine, name) -> None:
        super().__init__(engine, name)

    def activate(self):
        amount = 1
        self.engine.player.fighter.base_hp += amount
        self.message(f"{self.prefix} {amount} Max HP {self.postfix}")
