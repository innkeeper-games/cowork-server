from .item import Item

class Checkpoint(Item):

    def __init__(self):
        super().__init__()
        self.cost = 25
        self.type = "furniture"
        self.category = "interactive"
        self.title = "Checkpoint"
        self.id_ = 5
