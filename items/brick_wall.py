from .item import Item

class BrickWall(Item):

    def __init__(self):
        super().__init__()
        self.cost = 10
        self.type = "furniture"
        self.category = "structure"
        self.title = "Brick Wall"
        self.id_ = 6
