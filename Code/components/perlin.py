import random
import numpy as np


def build_map_new(shape):
    world = np.zeros(shape)
    for x in range(shape[0]):
        for y in range(shape[1]):
            world[x][y] = perlin()

    return world


def perlin():
    return random.randint(0, 100)
