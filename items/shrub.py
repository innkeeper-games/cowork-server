from .item import Item

class Shrub(Item):

    def __init__(self):
        super().__init__()
        self.cost = 25
        self.type = "furniture"
        self.category = "plants"
        self.title = "Shrub"
        self.id_ = 4
