from .item import Item

class WoodTile(Item):

    def __init__(self):
        super().__init__()
        self.cost = 5
        self.type = "furniture"
        self.category = "tile"
        self.title = "Wood Tile"
        self.id_ = 7
