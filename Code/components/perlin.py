import random

# import noise
import numpy as np


def build_map_new(shape):
    seed = random.randint(0, 1000000)
    world = np.zeros(shape)
    for x in range(shape[0]):
        for y in range(shape[1]):
            world[x][y] = perlin(x=x, y=y, seed=seed)

    return world


def perlin(x, y, seed):
    return random.randint(0, 100)

