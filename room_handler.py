from handler import Handler
from room_database_connector import RoomDatabaseConnector
from settings_database_connector import SettingsDatabaseConnector
from timer_database_connector import TimerDatabaseConnector
from tasks_database_connector import TasksDatabaseConnector

from room import Room

import json
from uuid import uuid4
import logging

# key is type, value is dictionary of requirements and types
message_templates = {
    "set_target": {"type": "set_target", "position_x": int, "position_y": int},
    "warp_to_persist_object": {"type": "warp_to_perist_object", "id": str},
    "move_persist_object": {"type": "move_persist_object", "id": str, "position_x": int, "position_y": int},
    "rotate_persist_object": {"type": "rotate_persist_object", "id": str, "rotation": int},
    "set_display_name": {"type": "set_display_name", "display_name": str, "id": str},
    "add_persist_object": {"type": "add_persist_object", "scene_id": int, "parent_id": str, \
        "rotation": int, "position_x": int, "position_y": int},
    "remove_persist_object": {"type": "remove_persist_object", "id": str},
    "place_tile": {"type": "place_tile", "position_x": int, "position_y": int, "tile_id": int},
    "remove_tile": {"type": "remove_tile", "position_x": int, "position_y": int},
    "request_wealth": {"type": "request_wealth"},
    "request_items": {"type": "request_items"},
    "request_inventory": {"type": "request_inventory"},
    "buy_item": {"type": "buy_item", "item_id": int}
}

class RoomHandler(Handler):

    def __init__(self, authentication_handler, scheduler):
        self.authentication_handler = authentication_handler
        self.room_database_connector = RoomDatabaseConnector()
        self.rooms = {}
        self.rooms_by_websocket = {}
        self.scheduler = scheduler
        self.tasks_database_connector = TasksDatabaseConnector()
        self.timer_database_connector = TimerDatabaseConnector()
        self.settings_database_connector = SettingsDatabaseConnector()


    def is_valid(self, message):
        global message_templates
            
        return Handler.is_valid(self, message_templates, message)


    async def consumer(self, websocket, message):
        message_valid = self.is_valid(message)
        if message_valid:
            if websocket in self.rooms_by_websocket:
                await self.rooms_by_websocket[websocket].consumer(websocket, message)
        else:
            logging.error(
                "Message type is " + message["type"] + " " + str(message))
            logging.error(
                str(message_valid))


    async def remove_peer(self, websocket):
        if websocket in self.rooms_by_websocket:
            room = self.rooms_by_websocket.pop(websocket)
            empty = await room.remove_peer(websocket)
            if empty:
                self.rooms.pop(room.get_id())
    

    def get_room(self, room_id):
        if room_id in self.rooms:
            return self.rooms[room_id]
    

    def peer_in_room(self, websocket):
        return websocket in self.rooms_by_websocket.keys()
    

    def get_room_by_peer(self, websocket):
        return self.rooms_by_websocket[websocket]


    async def add_peer_to_room(self, websocket, room_id, account_id):
        print("Adding peer " + str(websocket) + " to the room...")
        room = None
        if room_id in self.rooms:
            room = self.rooms[room_id]
        else:
            new_room = Room(room_id, self.room_database_connector, self.scheduler, self.tasks_database_connector, self.timer_database_connector, self.settings_database_connector)
            self.rooms[room_id] = new_room
            room = self.rooms[room_id]
        if websocket in self.rooms_by_websocket.keys():
            print("That peer is already part of another room. Attempting to remove them...")
            await self.rooms_by_websocket[websocket].remove_peer(websocket)
        else:
            print("The peer is not part of any other rooms.")
        display_name = self.room_database_connector.get_display_name_for_id(account_id)
        await room.add_peer(websocket, account_id, display_name)
        self.rooms_by_websocket[websocket] = room