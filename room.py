import json
from persist_object import PersistObject
from secrets import token_urlsafe
from datetime import datetime, timedelta

from session import Session

from items.pine_tree import PineTree
from items.shrub import Shrub
from items.brick_wall import BrickWall

from items.chicken import Chicken

from items.checkpoint import Checkpoint

from items.wood_tile import WoodTile

from player import Player
from tile_map import TileMap

from secrets import token_urlsafe
import random

import asyncio
import threading

from persist_object_factory import make_object

from tasks_database_connector import TasksDatabaseConnector
from timer_database_connector import TimerDatabaseConnector
from settings_database_connector import SettingsDatabaseConnector

class Room:

    def __init__(self, id_, room_database_connector, scheduler, tasks_database_connector, timer_database_connector, settings_database_connector):
        self.peers = set()
        self.accounts = {}
        self.id_ = id_
        self.room_database_connector = room_database_connector
        self.tasks_database_connector = tasks_database_connector
        self.timer_database_connector = timer_database_connector
        self.settings_database_connector = settings_database_connector
        self.persist_objects = {}
        self.players = {}

        self.tiles = {}

        # in theory, each room can have different items for sale
        self.available_items = [
            PineTree(),
            Shrub(),
            BrickWall(),

            Chicken(),
            Checkpoint()
        ]

        self.items = {}
        for item in self.available_items:
            self.items[item.get_id()] = item
        
        self.sessions = {}

        self.scheduler = scheduler

        self.living_persist_objects = set()

        persist_objects = self.room_database_connector.get_persist_objects(self.id_)
        if persist_objects is not None:
            self.load_persist_objects(persist_objects)
        else:
            # make a new room
            self.generate()


    def get_id(self):
        return self.id_


    def get_peers(self):
        return self.peers


    async def consumer(self, websocket, message):
        if message["type"] == "set_target":
            await self.set_target(websocket, message)
        if message["type"] == "warp_to_persist_object":
            await self.warp_to_persist_object(websocket, message)
        if message["type"] == "add_persist_object":
            await self.add_persist_object(websocket, message)
        if message["type"] == "remove_persist_object":
            await self.remove_persist_object(websocket, message)
        if message["type"] == "place_tile":
            await self.place_tile(websocket, message)
        if message["type"] == "remove_tile":
            await self.remove_tile(websocket, message)
        if message["type"] == "move_persist_object":
            await self.move_persist_object(websocket, message)
        if message["type"] == "rotate_persist_object":
            await self.rotate_persist_object(websocket, message)
        if message["type"] == "set_display_name":
            await self.set_display_name(websocket, message)
        if message["type"] == "request_wealth":
            await self.request_wealth(websocket, message)
        if message["type"] == "request_inventory":
            await self.request_inventory(websocket, message)
        if message["type"] == "request_items":
            await self.request_items(websocket, message)
        if message["type"] == "buy_item":
            await self.buy_item(websocket, message)

    
    async def add_peer(self, websocket_peer, account_id, display_name):
        # add or look up a character/avatar
        # add the avatar/character to the room
        # TODO: for now, just make a new one
        # also, send the peer all the room persist objs
        if not websocket_peer in self.peers:
            self.peers.add(websocket_peer)
            if account_id in self.accounts:
                # prevent duplicate players
                self.remove_peer(self.accounts[account_id])
            self.accounts[account_id] = websocket_peer
            for obj in self.persist_objects.values():
                # TODO: send this all at once
                response = {}
                response["data"] = obj.get_dictionary_representation()
                response["channel"] = "room"
                response["type"] = "add_persist_object"
                response_json = json.dumps(response, default=str)
                await websocket_peer.send(response_json)
            # add the new player (it doesn't know who it is yet)
            id_ = account_id
            active_listing_id = self.tasks_database_connector.get_active_listing_id(account_id)
            self.players[websocket_peer] = Player(account_id, id_, active_listing_id)
            await self.load_persist_object(1, id_, "root", "player", display_name=display_name, position_x=128*4, position_y=128*3)
        else:
            print("That peer is already a part of this room.")
    

    async def request_inventory(self, websocket, message):
        account_id = self.players[websocket].get_account_id()
        inventory = self.room_database_connector.get_inventory(account_id)
        inventory_details = []
        if inventory is not None:
            for item_id in inventory:
                item = self.items[int(item_id)]
                inventory_details.append({
                    "item_id": item.get_id(),
                    "type": item.get_type(),
                    "category": item.get_category(),
                    "quantity": inventory[item_id],
                    "title": item.get_title()
                })
        else:
            inventory_details = {}
        response = {"channel": "room", "type": "request_inventory", "inventory": inventory_details}
        response_json = json.dumps(response, default=str)
        await websocket.send(response_json)


    async def request_items(self, websocket, message):
        items = []
        for item in self.available_items:
            items.append({
                "item_id": item.get_id(),
                "type": item.get_type(),
                "category": item.get_category(),
                "cost": item.get_cost(),
                "title": item.get_title()
            })
        response = {"channel": "room", "type": "request_items", "items": items}
        response_json = json.dumps(response, default=str)
        await websocket.send(response_json)


    async def buy_item(self, websocket, message):
        # add item to inventory
        account_id = self.players[websocket].get_account_id()
        if message["item_id"] in self.items:
            wealth = self.room_database_connector.get_wealth_for_id(account_id)
            item = self.items[message["item_id"]]
            if wealth >= item.get_cost():
                self.room_database_connector.process_transaction(account_id, item)
                inventory = self.room_database_connector.get_inventory(account_id)

                if inventory is None:
                    inventory = {}
                if str(item.get_id()) in inventory:
                    inventory[str(item.get_id())] = inventory[str(item.get_id())] + 1
                else:
                    inventory[str(item.get_id())] = 1

                self.room_database_connector.save_inventory(account_id, json.dumps(inventory, default=str))

                response = {"channel": "room", "type": "buy_item", "item_id": item.get_id()}
                response_json = json.dumps(response, default=str)
                await websocket.send(response_json)

                response = {"channel": "room", "type": "request_wealth", "wealth": wealth - item.get_cost()}
                response_json = json.dumps(response, default=str)
                await websocket.send(response_json)


    async def move_chicken(self, id_):
        position = [random.randrange(0, 128 * 9), random.randrange(0, 128 * 6)]
        if len(self.peers) > 0 and id_ in self.persist_objects:
            self.scheduler.create_task(self.move_chicken, random.randrange(0, 30), id_)
            await self.set_persist_object_target(position, id_)


    async def set_persist_object_target(self, position, id_):
        response = {"channel": "room", "type": "modify_persist_object", "method": "set_target", "id": id_, \
            "position_x": position[0], "position_y": position[1]}
        self.persist_objects[id_].set_position(position[0], position[1])
        response_json = json.dumps(response, default=str)
        for peer in self.players:
            await peer.send(response_json)


    async def set_display_name(self, websocket, message):
        account_id = self.players[websocket].get_account_id()
        if message["id"] in self.persist_objects and self.has_permission(account_id):
            persist_object = self.persist_objects[message["id"]]
            position = persist_object.get_position()
            response = {"channel": "room", "type": "modify_persist_object", "method": "set_display_name", "id": persist_object.get_id(), \
                "display_name": message["display_name"]}
            persist_object.set_display_name(message["display_name"])
            response_json = json.dumps(response, default=str)
            for peer in self.players:
                await peer.send(response_json)


    async def set_target(self, websocket, message):
        position = (message["position_x"], message["position_y"])
        response = {"channel": "room", "type": "modify_persist_object", "method": "set_target", "id": self.players[websocket].get_id(), \
            "position_x": position[0], "position_y": position[1]}
        self.persist_objects[self.players[websocket].get_id()].set_position(position[0], position[1])
        response_json = json.dumps(response, default=str)
        for peer in self.players:
            await peer.send(response_json)


    async def warp_to_persist_object(self, websocket, message):
        account_id = self.players[websocket].get_account_id()
        if message["id"] in self.persist_objects:
            persist_object = self.persist_objects[message["id"]]
            position = persist_object.get_position()
            response = {"channel": "room", "type": "modify_persist_object", "method": "warp_to", "id": self.players[websocket].get_id(), \
                "position_x": position[0], "position_y": position[1]}
            self.persist_objects[self.players[websocket].get_id()].set_position(position[0], position[1])
            response_json = json.dumps(response, default=str)
            for peer in self.players:
                await peer.send(response_json)


    async def request_wealth(self, websocket, message):
        account_id = self.players[websocket].get_account_id()
        wealth = self.room_database_connector.get_wealth_for_id(account_id)
        response = {"channel": "room", "type": "request_wealth", "wealth": wealth}
        response_json = json.dumps(response, default=str)
        await websocket.send(response_json)


    def get_time_since_start_of_session(self, session_id):
        return self.sessions[session_id].get_time_since_start()


    async def add_persist_object(self, websocket, message):
        account_id = self.players[websocket].get_account_id()
        if self.has_permission(account_id):
            # this user is the owner and has the right to add new objects

            inventory = self.room_database_connector.get_inventory(account_id)
            item_id = str(message["scene_id"])
            if inventory is None:
                    inventory = {}
            if item_id in inventory:
                inventory[item_id] = inventory[item_id] - 1
                if inventory[item_id] == 0:
                    inventory.pop(item_id)
                
                response = {"channel": "room", "type": "remove_item", "item_id": item_id}
                response_json = json.dumps(response, default=str)
                await websocket.send(response_json)

                id_ = token_urlsafe(8)
                scene_id = message["scene_id"]
                parent_id = message["parent_id"]
                position_x = message["position_x"]
                position_y = message["position_y"]
                rotation = message["rotation"]

                await self.load_persist_object(scene_id, id_, parent_id, account_id, position_x=position_x, position_y=position_y, rotation=rotation)

            self.room_database_connector.save_inventory(account_id, json.dumps(inventory, default=str))


    async def remove_persist_object(self, websocket, message):
        account_id = self.players[websocket].get_account_id()
        persist_object_id = message["id"]
        if self.has_permission(account_id):
            # this user is the owner and has the right to remove objects

            if persist_object_id in self.persist_objects:
                persist_object = self.persist_objects[persist_object_id]
                owner_account_id = persist_object.get_owner_account_id()
                item = self.items[persist_object.get_scene_id()]

                inventory = self.room_database_connector.get_inventory(owner_account_id)

                if inventory is None:
                    inventory = {}
                if str(item.get_id()) in inventory:
                    inventory[str(item.get_id())] = inventory[str(item.get_id())] + 1
                else:
                    inventory[str(item.get_id())] = 1

                self.room_database_connector.save_inventory(owner_account_id, json.dumps(inventory, default=str))

                self.persist_objects.pop(persist_object.get_id())
                response = {"channel": "room", "type": "remove_persist_object", "id": persist_object.get_id()}
                response_json = json.dumps(response, default=str)
                for peer in self.players:
                    await peer.send(response_json)


    async def place_tile(self, websocket, message):
        pass


    async def place_tile(self, websocket, message):
        pass


    async def move_persist_object(self, websocket, message):
        account_id = self.players[websocket].get_account_id()
        persist_object_id = message["id"]
        position = (message["position_x"], message["position_y"])
        if self.has_permission(account_id):
            # this user is the owner and has the right to move objects

            if persist_object_id in self.persist_objects:
                response = {"channel": "room", "type": "modify_persist_object", "method": "move", "id": persist_object_id, \
                    "position_x": position[0], "position_y": position[1]}
                self.persist_objects[persist_object_id].set_position(position[0], position[1])
                response_json = json.dumps(response, default=str)
                for peer in self.players:
                    await peer.send(response_json)


    async def rotate_persist_object(self, websocket, message):
        account_id = self.players[websocket].get_account_id()
        persist_object_id = message["id"]
        rotation = message["rotation"]
        if self.has_permission(account_id):
            # this user is the owner and has the right to move objects

            if persist_object_id in self.persist_objects:
                response = {"channel": "room", "type": "modify_persist_object", "method": "rotate", "id": persist_object_id, \
                    "rotation": rotation}
                self.persist_objects[persist_object_id].set_rotation(rotation)
                response_json = json.dumps(response, default=str)
                for peer in self.players:
                    await peer.send(response_json)


    async def load_persist_object(self, scene_id, id_, parent_id, owner_account_id, rotation=0, position_x=0, position_y=0, display_name=""):
        persist_object = PersistObject(scene_id, id_, parent_id, owner_account_id, rotation, position_x, position_y, display_name)
        if scene_id == 3:
            self.scheduler.create_task(self.move_chicken, random.randrange(0, 30), id_)
        self.persist_objects[id_] = persist_object
        response = {}
        response["data"] = persist_object.get_dictionary_representation()
        response["channel"] = "room"
        response["type"] = "add_persist_object"
        response_json = json.dumps(response, default=str)
        for peer in self.players:
            await peer.send(response_json)


    async def remove_peer(self, websocket_peer):
        self.peers.discard(websocket_peer)
        if websocket_peer in self.players:
            player = self.players[websocket_peer]
            if player.is_in_session():
                self.remove_peer_from_session(websocket_peer)
            self.players.pop(websocket_peer)
            self.persist_objects.pop(player.get_id())
            response = {"channel": "room", "type": "remove_persist_object", "id": player.get_id()}
            response_json = json.dumps(response, default=str)
            for peer in self.players:
                await peer.send(response_json)
        if len(self.peers) == 0:
            self.room_database_connector.save_persist_objects(self.id_, self.get_save_json())
            return True
        return False


    def has_permission(self, account_id):
        return True


    def load_persist_objects(self, new_persist_objects):
        objs = new_persist_objects["persist_objects"]
        for obj in objs:
            persist_object = make_object(obj["scene_id"], obj)
            if obj["scene_id"] == 3:
                self.scheduler.create_task(self.move_chicken, random.randrange(0, 30), obj["id"])
            self.persist_objects[obj["id"]] = persist_object


    def generate(self):
        # make a blank room scene, and that's it really
        # in the future, this should proc. gen. a map for the room
        chicken_count = random.randrange(2, 6)
        for i in range(chicken_count):
            id_ = token_urlsafe(8)
            chicken = PersistObject(3, id_, "root", "root", 0, random.randrange(0, 128 * 9), random.randrange(0, 128 * 6), "Chicken")
            self.persist_objects[id_] = chicken
            self.scheduler.create_task(self.move_chicken, random.randrange(0, 30), id_)
        # position tuple: {owner_account_id, 0}
        layers = {
            (0, 0): ["root", 0]
        }
        floor = TileMap(0, "root", None, 16, 8, layers)
        self.persist_objects["root"] = floor


    def get_save_json(self):
        persist_object_dictionaries = []
        for obj in self.persist_objects.values():
            dictionary_representation = obj.get_dictionary_representation()
            if not dictionary_representation["scene_id"] == 1:
                # only save this object if it is not a player.
                # TODO: kick players before saving?
                persist_object_dictionaries.append(dictionary_representation)
        return json.dumps({
            "tiles": self.tiles,
            "persist_objects": persist_object_dictionaries
        }, default=str)
    

    def add_session(self, consumable, duration_minutes, is_break):
        session_id = self.timer_database_connector.add_session(consumable, self.id_, is_break)
        start_time = datetime.now()
        duration = timedelta(minutes=duration_minutes)
        self.sessions[session_id] = Session(session_id, consumable, start_time, duration, self.timer_database_connector)
        return session_id


    def get_sessions(self):
        # probably should actually return the sessions objects?
        # this exposes its properties for jsonificiation later
        return self.sessions.values()


    def get_session(self, session_id):
        return self.sessions[session_id]


    def has_session_id(self, session_id):
        return session_id in self.sessions.keys()


    def add_peer_to_session(self, websocket, session_id):
        # active task might be None
        if not self.players[websocket].is_in_session():
            self.sessions[session_id].add_participant(self.players[websocket].get_account_id(), self.players[websocket].get_active_listing_id())
            self.players[websocket].set_active_session_id(session_id)


    async def on_peer_changed_active_listing_id(self, websocket, listing_id):
        self.players[websocket].set_active_listing_id(listing_id)
        account_id = self.players[websocket].get_account_id()
        if self.players[websocket].is_in_session():
            self.sessions[self.players[websocket].get_active_session_id()].create_span(account_id, listing_id)
        task = self.tasks_database_connector.get_task_for_listing(listing_id)
        public = task[1]
        response = {
            "channel": "room", 
            "type": "peer_changed_active_listing",
            "public": public
        }
        if public:
            response["task_id"] = task[0]
            response["active"] = task[2]
            response["title"] = task[3]
            response["contents"] = task[4]
            response["room_id"] = task[5]
        response["persist_object_id"] = self.players[websocket].get_id()
        response_json = json.dumps(response, default=str)
        for peer in self.players:
            await peer.send(response_json)


    def remove_peer_from_session(self, websocket):
        if self.players[websocket].is_in_session():
            session_id = self.players[websocket].get_active_session_id()
            self.players[websocket].set_active_session_id(None)
            self.sessions[session_id].remove_participant(self.players[websocket].get_account_id())
            # TODO: inform others that this participant has left the session
            if len(self.sessions[session_id].get_participants()) == 0:
                # Erase the session.
                # TODO: Inform everyone in the room that this session has ended;
                # there are no more participants
                self.sessions.pop(session_id)
                return True
        return False


    def set_active_listing_id(self, websocket, listing_id):
        self.players[websocket].set_active_listing_id(listing_id)
