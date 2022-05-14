from .item import Item

class PineTree(Item):

    def __init__(self):
        super().__init__()
        self.cost = 25
        self.type = "furniture"
        self.category = "plants"
        self.title = "Pine Tree"
        self.id_ = 2
