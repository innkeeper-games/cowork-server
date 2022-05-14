from .item import Item

class Chicken(Item):

    def __init__(self):
        super().__init__()
        self.cost = 100
        self.type = "furniture"
        self.category = "animals"
        self.title = "Chicken"
        self.id_ = 3
