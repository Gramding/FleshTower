from typing import Tuple

class Entity:
    #this is a generic class to represent every entity in game
    #the player enemies items etc.

    def __init__(self,x: int,y: int, char: str, color:Tuple[int,int,int]):
        #set object variables
        self.x = x #cords of entity
        self.y = y
        self.char = char #this is the character that represents the entity (player = @)
        self.color = color #color of entity

    def move(self, dx:int,dy: int) -> None:
        self.x += dx
        self.y += dy
        