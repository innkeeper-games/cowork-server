class PersistObject:
    
    def __init__(self, scene_id, id_, parent_id, owner_account_id, rotation, position_x, position_y, display_name):
        self.scene_id = scene_id
        self.id_ = id_
        self.parent_id = parent_id
        self.owner_account_id = owner_account_id
        self.rotation = rotation
        self.position_x = position_x
        self.position_y = position_y
        self.display_name = display_name
    

    def set_rotation(self, rotation):
        self.rotation = rotation
    

    def set_position(self, position_x, position_y):
        self.position_x = position_x
        self.position_y = position_y


    def set_display_name(self, display_name):
        if display_name == "":
            display_name = None
        self.display_name = display_name


    def get_scene_id(self):
        return self.scene_id
    

    def get_id(self):
        return self.id_


    def get_position(self):
        return (self.position_x, self.position_y)


    def get_owner_account_id(self):
        return self.owner_account_id


    def get_dictionary_representation(self):
        return {
            "scene_id": self.scene_id,
            "id": self.id_,
            "parent_id": self.parent_id,
            "owner_account_id": self.owner_account_id,
            "rotation": self.rotation,
            "position_x": self.position_x,
            "position_y": self.position_y,
            "display_name": self.display_name
        }
        