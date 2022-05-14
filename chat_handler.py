from handler import Handler
from chat_database_connector import ChatDatabaseConnector

from datetime import datetime

import json
from uuid import uuid4
import logging
import asyncio
from settings_database_connector import SettingsDatabaseConnector

# key is type, value is dictionary of requirements and types
message_templates = {
    "request_initial_messages": {"type": "request_initial_messages", "room_id": str},
    "request_messages": {"type": "request_messages", "room_id": str, "before_chat_id": str},
    "send_message": {"type": "send_message", "room_id": str, "contents": str},
    "delete_message": {"type": "delete_message", "chat_id": str},
    "edit_message": {"type": "edit_message", "chat_id": str, "new_contents": str},
    #"react_to_message": {"type": "react_to_message", "room_id": str, "chat_id": str, "reaction": str}
}

class ChatHandler(Handler):

    def __init__(self, authentication_handler, room_handler):
        self.authentication_handler = authentication_handler
        self.room_handler = room_handler
        self.chat_database_connector = ChatDatabaseConnector()
        self.settings_database_connector = SettingsDatabaseConnector()


    def is_valid(self, message):
        global message_templates
            
        return Handler.is_valid(self, message_templates, message)


    async def consumer(self, websocket, message):
        message_valid = self.is_valid(message)
        if message_valid:
            if message["type"] == "request_initial_messages":
                await self.request_initial_messages(websocket, message)
            elif message["type"] == "request_messages":
                await self.request_messages(websocket, message)
            elif message["type"] == "send_message":
                await self.send_message(websocket, message)
            elif message["type"] == "edit_message":
                await self.edit_message(websocket, message)
            elif message["type"] == "delete_message":
                await self.delete_message(websocket, message)
        else:
            logging.error(
                "Message type is " + message["type"] + " " + str(message))
            logging.error(
                str(message_valid))


    async def request_messages(self, websocket, message):
        # reply with a set of 10 messages
        username = self.authentication_handler.usernames[websocket]
        account_id = self.chat_database_connector.get_id_for_username(username)
        room_id = message["room_id"]
        messages_a = []
        if self.settings_database_connector.membership_exists(account_id, room_id):
            messages = self.chat_database_connector.get_chats_for_room(room_id, 10, message["before_chat_id"])
            for message in messages:
                message_a = {}
                message_a["chat_id"] = message[0]
                message_a["account_id"] = message[1]
                message_a["display_name"] = self.chat_database_connector.get_display_name_for_id(message[1])
                message_a["sent_date"] = message[2]
                message_a["contents"] = message[3]
                message_a["edited"] = message[4]
                messages_a.append(message_a)
        response = {"channel": "chat", "type": "request_messages", "messages": messages_a}
        response_json = json.dumps(response, default=str)
        await websocket.send(response_json)


    async def request_initial_messages(self, websocket, message):
        # reply with a set of 10 messages
        print("retrieving initial messages")
        username = self.authentication_handler.usernames[websocket]
        account_id = self.chat_database_connector.get_id_for_username(username)
        room_id = message["room_id"]
        messages_a = []
        if self.settings_database_connector.membership_exists(account_id, room_id):
            messages = self.chat_database_connector.get_chats_for_room(room_id, 10)
            for message in messages:
                message_a = {}
                message_a["chat_id"] = message[0]
                message_a["account_id"] = message[1]
                message_a["display_name"] = self.chat_database_connector.get_display_name_for_id(message[1])
                message_a["sent_date"] = message[2]
                message_a["contents"] = message[3]
                message_a["edited"] = message[4]
                messages_a.append(message_a)
        response = {"channel": "chat", "type": "request_messages", "messages": messages_a}
        response_json = json.dumps(response, default=str)
        await websocket.send(response_json)


    async def send_message(self, websocket, message):
        # create a message in the database and
        # add the chat to the room
        username = self.authentication_handler.usernames[websocket]
        account_id = self.chat_database_connector.get_id_for_username(username)
        room_id = message["room_id"]
        contents = message["contents"]
        if self.settings_database_connector.membership_exists(account_id, room_id) and len(contents) > 0:
            # do not save chat messages in listed rooms
            chat_id = None
            if not room_id in self.room_handler.settings_database_connector.get_listed_rooms():
                chat_id = self.chat_database_connector.add_chat_message(account_id, room_id, contents)
            display_name = self.chat_database_connector.get_display_name_for_id(account_id)
            room = self.room_handler.get_room(room_id)
            peers = room.get_peers()
            if websocket in peers:
                response = {"channel": "chat", "type": "send_message", "display_name": display_name, "account_id": account_id, "sent_date": self.chat_database_connector.get_time_for_chat(chat_id), "contents": contents, "chat_id": chat_id, "edited": False}
                response_json = json.dumps(response, default=str)
                for peer in peers:
                    await peer.send(response_json)


    async def edit_message(self, websocket, message):
        # edit a message in the database and
        # edit that chat in the room
        username = self.authentication_handler.usernames[websocket]
        account_id = self.chat_database_connector.get_id_for_username(username)
        chat_id = message["chat_id"]
        new_contents = message["new_contents"]
        if self.chat_database_connector.chat_exists(chat_id):
            room_id = self.chat_database_connector.get_room_id_for_chat(chat_id)
            if account_id == self.chat_database_connector.get_account_id_for_chat(chat_id):
                if not room_id in self.room_handler.settings_database_connector.get_listed_rooms():
                    self.chat_database_connector.edit_chat(chat_id, new_contents)
                room = self.room_handler.get_room(room_id)
                peers = room.get_peers()
                if websocket in peers:
                    response = {"channel": "chat", "type": "edit_message", "chat_id": chat_id, "new_contents": new_contents}
                    response_json = json.dumps(response, default=str)
                    for peer in peers:
                        await peer.send(response_json)


    async def delete_message(self, websocket, message):
        # delete a message in the database and
        # delete the chat from the room
        # TODO: allow mods to delete chats
        username = self.authentication_handler.usernames[websocket]
        account_id = self.chat_database_connector.get_id_for_username(username)
        chat_id = message["chat_id"]
        if self.chat_database_connector.chat_exists(chat_id):
            room_id = self.chat_database_connector.get_room_id_for_chat(chat_id)
            if account_id == self.chat_database_connector.get_account_id_for_chat(chat_id) or account_id == self.settings_database_connector.get_room_owner_account_id(room_id):
                if not room_id in self.room_handler.settings_database_connector.get_listed_rooms():
                    self.chat_database_connector.delete_chat(chat_id)
                room = self.room_handler.get_room(room_id)
                peers = room.get_peers()
                if websocket in peers:
                    response = {"channel": "chat", "type": "delete_message", "chat_id": chat_id}
                    response_json = json.dumps(response, default=str)
                    for peer in peers:
                        await peer.send(response_json)
