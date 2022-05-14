from abc import ABC

class Item(ABC):

    def __init__(self):
        self.cost = 0
        self.category = ""
        self.title = ""
        self.type = ""
        self.id_ = 0

    def get_cost(self):
        return self.cost

    def get_type(self):
        return self.type

    def get_category(self):
        return self.category

    def get_title(self):
        return self.title

    def get_id(self):
        return self.id_