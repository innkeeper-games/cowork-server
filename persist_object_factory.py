from persist_object import PersistObject
from tile_map import TileMap

def make_object(scene_id, data):
    if scene_id == 0:
        # tile map
        return TileMap(scene_id, data["id"], data["parent_id"], \
            data["layers"])
    else:
        display_name = ""
        rotation = 0
        if "display_name" in data:
            display_name = data["display_name"]
        if "rotation_degrees_y" in data:
            rotation = data["rotation_degrees_y"]
        else:
            rotation = data["rotation"]
        return PersistObject(scene_id, data["id"], data["parent_id"], data["owner_account_id"], rotation, \
            data["position_x"], data["position_y"], display_name)
