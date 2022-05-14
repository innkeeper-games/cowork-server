import accounts

from handler import Handler
from emailer import Emailer

import json
from uuid import uuid4
from secrets import token_urlsafe
import logging
import re

EMAIL_REGEX = re.compile(r"[^@]+@[^@]+\.[^@]+")

# key is type, value is dictionary of requirements and types
message_templates = {
    "sign_out": {"type": "sign_out"},
    "pong": {"type": "pong"}
}

class AuthenticationHandler(Handler):

    def __init__(self, scheduler, sign_up_enabled=True):
        self.auth_database_connector = accounts.AccountsDatabaseConnector()
        self.usernames = {}
        self.emailer = Emailer()
        self.scheduler = scheduler


    def is_valid(self, message):
        global message_templates
            
        return Handler.is_valid(self, message_templates, message)


    def set_auth_websocket(self, auth_websocket):
        self.auth_websocket = auth_websocket


    async def consumer(self, websocket, message):
        if (self.is_valid(message)):
            if message["type"] == "sign_out":
                await self.sign_out(websocket)
            elif message["type"] == "pong":
                await self.pong(websocket)
            else:
                logging.error(
                    "Message type is " + message["type"] + " " + str(message))


    async def pong(self, websocket):
        response = {"channel": "auth", "type": "ping"}
        response_json = json.dumps(response, default=str)
        await self.scheduler.run()
        await websocket.send(response_json)


    def make_session(self, websocket, username):
        account_id = self.auth_database_connector.get_id_for_username(username)
        self.usernames[websocket] = username


    async def sign_out(self, websocket):
            
        if websocket in self.usernames:
            print("Signing out " + str(websocket))
            token = self.tokens[websocket]
            self.usernames.pop(websocket, None)
        response = {"channel": "auth", "type": "sign_out", "success": True}
        response_json = json.dumps(response, default=str)
        await websocket.send(response_json)


    def remove_client(self, websocket):
        return self.usernames.pop(websocket, None)
    
