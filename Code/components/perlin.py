import random
import noise
import numpy as np

def build_map(shape):
    seed = random.randint(0,1000000)
    world = np.zeros(shape)
    for x in range(shape[0]):
        for y in range(shape[1]):
            chords = (x,y)
            world[x][y] = noise.snoise2(chords[0]/20, 
                         chords[1]/20,
                         octaves=6, #number of noise layers
                         persistence=0.5,
                         lacunarity=2,
                         repeatx=chords[0],
                         repeaty=chords[1],
                         base=seed
                         )
            world[x][y] = world[x][y]**2

    return world
