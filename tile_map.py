import persist_object

class TileMap(persist_object.PersistObject):

    def __init__(self, scene_id, id_, parent_id, layers, rotation_degrees_y=0, position_x=0, position_y=0):
        self.scene_id = scene_id
        self.id_ = id_
        self.parent_id = parent_id
        self.layers = layers
        self.rotation_degrees_y = rotation_degrees_y
        self.position_x = position_x
        self.position_y = position_y


    def get_dictionary_representation(self):
        return {
            "scene_id": self.scene_id,
            "id": self.id_,
            "parent_id": self.parent_id,
            "layers": self.layers,
            "rotation_degrees_y": self.rotation_degrees_y,
            "position_x": self.position_x,
            "position_y": self.position_y,
        }