from handler import Handler
from timer_database_connector import TimerDatabaseConnector

from datetime import datetime

import math

import json
from uuid import uuid4
import logging
import asyncio
from settings_database_connector import SettingsDatabaseConnector

# key is type, value is dictionary of requirements and types
message_templates = {
    "start_session": {"type": "start_session", "room_id": str, "consumable": int, "duration": int, "is_break": bool},
    "leave_session": {"type": "leave_session", "room_id": str, "session_id": str},
    "join_session": {"type": "join_session", "room_id": str, "session_id": str},
    "request_active_sessions": {"type": "request_active_sessions", "room_id": str}
}

class TimerHandler(Handler):

    def __init__(self, authentication_handler, room_handler, scheduler):
        self.authentication_handler = authentication_handler
        self.room_handler = room_handler
        self.scheduler = scheduler
        self.timer_database_connector = TimerDatabaseConnector()
        self.settings_database_connector = SettingsDatabaseConnector()
        self.sessions = {}


    def is_valid(self, message):
        global message_templates
            
        return Handler.is_valid(self, message_templates, message)


    async def consumer(self, websocket, message):
        message_valid = self.is_valid(message)
        session_valid = False
        if message_valid:
            if message["type"] == "start_session":
                await self.start_session(websocket, message)
            elif message["type"] == "leave_session":
                await self.leave_session(websocket, message)
            elif message["type"] == "join_session":
                await self.join_session(websocket, message)
            elif message["type"] == "request_active_sessions":
                await self.request_active_sessions(websocket, message)
        else:
            logging.error(
                "Message type is " + message["type"] + " " + str(message))
            logging.error(
                str(message_valid) + " " + str(session_valid))


    async def start_session(self, websocket, message):
        username = self.authentication_handler.usernames[websocket]
        account_id = self.timer_database_connector.get_id_for_username(username)
        room_id = message["room_id"]
        if self.settings_database_connector.membership_exists(account_id, room_id):
            # TODO: validate that this user has (some of?) that consumable.
            user_has_consumable = True
            if user_has_consumable:
                room = self.room_handler.get_room(room_id)
                session_id = room.add_session(message["consumable"], message["duration"], message["is_break"])
                room.add_peer_to_session(websocket, session_id)
                peers = room.get_peers()
                session = room.get_session(session_id)
                if websocket in peers:
                    display_name = self.settings_database_connector.get_display_name_for_id(account_id)
                    response = {"channel": "timer", "type": "start_session", "session_id": session_id, "participants": [{"display_name": display_name, "account_id": account_id}], \
                        "consumable": message["consumable"], "duration": message["duration"], "expected_end_time": session.get_expected_end_time(), "is_break": message["is_break"]}
                    response_json = json.dumps(response, default=str)
                    self.scheduler.create_task(self.end_session, message["duration"] * 60, room_id, session_id)
                    for peer in peers:
                        await peer.send(response_json)


    async def end_session(self, room_id, session_id):
        room = self.room_handler.get_room(room_id)
        if room is not None:
            if room.has_session_id(session_id):
                session = room.get_session(session_id)
                peers = room.get_peers()
                response = {"channel": "timer", "type": "end_session", "session_id": session_id}
                response_json = json.dumps(response, default=str)
                for peer in peers:
                    await peer.send(response_json)

                    username = self.authentication_handler.usernames[peer]
                    account_id = self.timer_database_connector.get_id_for_username(username)

                    if self.room_handler.get_room(room_id).has_session_id(session_id):
                        if account_id in self.room_handler.get_room(room_id).get_session(session_id).get_spans():
                            # TODO: this will over-reward participants who join late
                            time = math.floor(room.get_time_since_start_of_session(session_id).total_seconds() / float(60))
                            # TODO: participant multiplier
                            self.room_handler.timer_database_connector.add_wealth(account_id, time)
                            wealth = self.room_handler.room_database_connector.get_wealth_for_id(account_id)
                            response = {"channel": "room", "type": "request_wealth", "wealth": wealth}
                            response_json = json.dumps(response, default=str)
                            await peer.send(response_json)

                            empty = room.remove_peer_from_session(peer)


    async def request_active_sessions(self, websocket, message):
        # reply with a set of 10 messages
        username = self.authentication_handler.usernames[websocket]
        account_id = self.timer_database_connector.get_id_for_username(username)
        room_id = message["room_id"]
        sessions_a = []
        if self.settings_database_connector.membership_exists(account_id, room_id):
            sessions = self.room_handler.get_room(room_id).get_sessions()
            for session in sessions:
                session_a = {}
                session_a["expected_end_time"] = session.get_expected_end_time()
                participant_account_ids = session.get_participants()
                participants = []
                for participant_account_id in participant_account_ids:
                    display_name = self.timer_database_connector.get_display_name_for_id(participant_account_id)
                    participants.append({"display_name": display_name, "account_id": participant_account_id})
                session_a["participants"] = participants
                session_a["consumable"] = session.get_consumable()
                session_a["session_id"] = session.get_id()
                sessions_a.append(session_a)
        response = {"channel": "timer", "type": "request_active_sessions", "messages": sessions_a}
        response_json = json.dumps(response, default=str)
        await websocket.send(response_json)


    async def join_session(self, websocket, message):
        username = self.authentication_handler.usernames[websocket]
        account_id = self.timer_database_connector.get_id_for_username(username)
        room_id = message["room_id"]
        response = {"channel": "timer", "type": "join_session", "success": False}
        if self.settings_database_connector.membership_exists(account_id, room_id):
            room = self.room_handler.get_room(room_id)
            if room.has_session_id(message["session_id"]):
                room.add_peer_to_session(websocket, message["session_id"])
                session = room.get_session(message["session_id"])
                peers = room.get_peers()
                participant_account_ids = session.get_participants()
                participants = []
                for participant_account_id in participant_account_ids:
                    display_name = self.timer_database_connector.get_display_name_for_id(participant_account_id)
                    participants.append({"display_name": display_name, "account_id": participant_account_id})
                if websocket in peers:
                    display_name = self.settings_database_connector.get_display_name_for_id(account_id)
                    response = {"channel": "timer", "type": "join_session", "success": True, "display_name": display_name, \
                        "session_id": message["session_id"], "participants": participants, "expected_end_time": session.get_expected_end_time()}
                    response_json = json.dumps(response, default=str)
                    for peer in peers:
                        await peer.send(response_json)
                return
        response_json = json.dumps(response, default=str)
        await websocket.send(response_json)


    async def leave_session(self, websocket, message):
        username = self.authentication_handler.usernames[websocket]
        account_id = self.timer_database_connector.get_id_for_username(username)
        room_id = message["room_id"]
        response = {"channel": "timer", "type": "leave_session", "success": False}
        if self.settings_database_connector.membership_exists(account_id, room_id):
            room = self.room_handler.get_room(room_id)
            if room.has_session_id(message["session_id"]):

                time = math.floor(room.get_time_since_start_of_session(message["session_id"]).total_seconds() / float(60))
                # TODO: participant multiplier
                self.room_handler.timer_database_connector.add_wealth(account_id, time)
                wealth = self.room_handler.room_database_connector.get_wealth_for_id(account_id)
                response = {"channel": "room", "type": "request_wealth", "wealth": wealth}
                response_json = json.dumps(response, default=str)
                await websocket.send(response_json)

                empty = room.remove_peer_from_session(websocket)

                peers = room.get_peers()
                if websocket in peers:
                    display_name = self.settings_database_connector.get_display_name_for_id(account_id)
                    response = {"channel": "timer", "type": "leave_session", "success": True, "display_name": display_name, \
                        "session_id": message["session_id"]}
                    response_json = json.dumps(response, default=str)
                    for peer in peers:
                        await peer.send(response_json)
                    if empty:
                        response = {"channel": "timer", "type": "end_session", "session_id": message["session_id"]}
                        response_json = json.dumps(response, default=str)
                        for peer in peers:
                            await peer.send(response_json)
                return
        response_json = json.dumps(response, default=str)
        await websocket.send(response_json)

