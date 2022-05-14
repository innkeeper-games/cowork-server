from handler import Handler
from settings_database_connector import SettingsDatabaseConnector
from emailer import Emailer

import braintree, os

import json
from uuid import uuid4
import logging

import re

EMAIL_REGEX = re.compile(r"[^@]+@[^@]+\.[^@]+")

# key is type, value is dictionary of requirements and types
message_templates = {
    "request_payment_client_token": {"type": "request_payment_client_token"},
    "checkout": {"type": "checkout", "payment_nonce": str, "device_data": str},
    "edit_display_name": {"type": "edit_display_name", "display_name": str},
    "enter_room": {"type": "enter_room", "room_id": str},
    "create_room": {"type": "create_room", "title": str},
    "join_room": {"type": "join_room", "room_id": str},
    "leave_room": {"type": "leave_room", "room_id": str},
    "request_rooms": {"type": "request_rooms"},
    "request_listed_rooms": {"tye": "request_listed_rooms"},
    "edit_room_title": {"type": "edit_room_title", "room_title": str},
    "edit_room_description": {"type": "edit_room_description", "room_description": str},
    "set_room_privacy": {"type": "set_room_privacy", "room_id": str, "private": bool},
    "request_room_privacy": {"type": "request_room_privacy", "room_id": str},
    "create_invitation": {"type": "create_invitation", "room_id": str, "invitee": str},
    "request_invitations": {"type": "request_invitations"},
    "decline_invitation": {"type": "decline_invitation", "invitation_id": str},
    "request_room_members": {"type": "request_room_members", "room_id": str}
}

class SettingsHandler(Handler):

    def __init__(self, authentication_handler, room_handler):
        self.authentication_handler = authentication_handler
        self.room_handler = room_handler
        self.settings_database_connector = SettingsDatabaseConnector()
        self.emailer = Emailer()
        self.gateway = braintree.BraintreeGateway(
            braintree.Configuration(
                braintree.Environment.Sandbox,
                merchant_id=os.environ.get("BRAINTREE_MERCHANT_ID"),
                public_key=os.environ.get("BRAINTREE_PUBLIC_KEY"),
                private_key=os.environ.get("BRAINTREE_PRIVATE_KEY")
            )
        )


    def is_valid(self, message):
        global message_templates
            
        return Handler.is_valid(self, message_templates, message)


    async def consumer(self, websocket, message):
        message_valid = self.is_valid(message)
        if message_valid:
            await getattr(self, message["type"])(websocket, message)
        else:
            logging.error(
                "Message type is " + message["type"] + " " + str(message))
            logging.error(
                str(message_valid))


    async def request_payment_client_token(self, websocket, message):
        username = self.authentication_handler.usernames[websocket]
        client_token = self.gateway.client_token.generate()
        response = {"channel": "settings", "type": "request_payment_client_token", "token": client_token}
        response_json = json.dumps(response, default=str)
        await websocket.send(response_json)


    async def checkout(self, websocket, message):
        username = self.authentication_handler.usernames[websocket]
        account_id = self.settings_database_connector.get_id_for_username(username)

        nonce_from_the_client = message["payment_nonce"]
        device_data_from_the_client = message["device_data"]

        result = self.gateway.customer.create({
            "email": username,
            "payment_method_nonce": nonce_from_the_client
        })

        if result.is_success:
            token = result.customer.payment_methods[0].token

            result = self.gateway.subscription.create({
                "payment_method_token": token,
                "plan_id": os.environ.get("BRAINTREE_PLAN_ID"),
                "options": {
                    "start_immediately": True
                }
            })

            print(result.subscription.status)
            success = result.subscription.status == braintree.Subscription.Status.Active
            if success:
                self.authentication_handler.auth_database_connector.set_pro(account_id, True)
                response = {"channel": "settings", "type": "checkout", "success": success}
                response_json = json.dumps(response, default=str)
                await websocket.send(response_json)


    async def edit_display_name(self, websocket, message):
        username = self.authentication_handler.usernames[websocket]
        account_id = self.settings_database_connector.get_id_for_username(username)
        new_display_name = message["display_name"]
        success = self.settings_database_connector.edit_display_name(account_id, new_display_name)
        response = {"channel": "settings", "type": "edit_display_name", "success": success, "display_name": new_display_name}
        response_json = json.dumps(response, default=str)
        await websocket.send(response_json)


    async def enter_room(self, websocket, message):
        # tell room that person has joined that room?
        # other indicator that person is online?
        # let them know it was successful maybe?
        username = self.authentication_handler.usernames[websocket]
        account_id = self.settings_database_connector.get_id_for_username(username)
        room_id = message["room_id"]
        success = False
        if self.settings_database_connector.membership_exists(account_id, room_id):
            success = True
            room_title = self.settings_database_connector.get_room_title(room_id)
            room_description = self.settings_database_connector.get_room_description(room_id)
            room_owner_account_id = self.settings_database_connector.get_room_owner_account_id(room_id)
            response = {"channel": "settings", "type": "enter_room", "success": success, "is_owner": room_owner_account_id == account_id, "room_id": room_id, "room_title": room_title, "room_description": room_description}
            response_json = json.dumps(response, default=str)
            await websocket.send(response_json)

            await self.room_handler.add_peer_to_room(websocket, room_id, account_id)

    
    async def join_room(self, websocket, message):
        success = False
        username = self.authentication_handler.usernames[websocket]
        account_id = self.settings_database_connector.get_id_for_username(username)
        success = self.settings_database_connector.create_membership(account_id, message["room_id"])
        response = {"channel": "settings", "type": "join_room", "success": success, "room_id": message["room_id"]}
        response_json = json.dumps(response, default=str)
        await websocket.send(response_json)
    

    async def leave_room(self, websocket, message):
        success = False
        username = self.authentication_handler.usernames[websocket]
        account_id = self.settings_database_connector.get_id_for_username(username)
        success = self.settings_database_connector.delete_membership(account_id, message["room_id"])
        response = {"channel": "settings", "type": "leave_room", "success": success}
        response_json = json.dumps(response, default=str)
        await websocket.send(response_json)


    async def create_room(self, websocket, message):
        username = self.authentication_handler.usernames[websocket]
        account_id = self.settings_database_connector.get_id_for_username(username)
        room_id = self.settings_database_connector.create_room(message["title"], account_id)
        response = {"channel": "settings", "type": "create_room", "room_id": room_id}
        response_json = json.dumps(response, default=str)
        await websocket.send(response_json)


    async def request_rooms(self, websocket, message):
        username = self.authentication_handler.usernames[websocket]
        rooms = self.settings_database_connector.get_rooms_for_username(username)
        for room_id in rooms:
            online = 0
            if self.room_handler.get_room(room_id) is not None:
                online = len(self.room_handler.get_room(room_id).get_peers())
            rooms[room_id]["online"] = online
        response = {"channel": "settings", "type": "request_rooms", "rooms": rooms}
        response_json = json.dumps(response, default=str)
        await websocket.send(response_json)


    async def request_listed_rooms(self, websocket, message):
        # TODO: what are the permissions like here?
        username = self.authentication_handler.usernames[websocket]
        listed_rooms = self.settings_database_connector.get_listed_rooms()
        for room_id in listed_rooms:
            online = 0
            if self.room_handler.get_room(room_id) is not None:
                online = len(self.room_handler.get_room(room_id).get_peers())
            listed_rooms[room_id]["online"] = online
        response = {"channel": "settings", "type": "request_listed_rooms", "listed_rooms": listed_rooms}
        response_json = json.dumps(response, default=str)
        await websocket.send(response_json)


    async def edit_room_title(self, websocket, message):
        username = self.authentication_handler.usernames[websocket]
        account_id = self.settings_database_connector.get_id_for_username(username)
        new_room_title = message["room_title"]
        room_id = message["room_id"]
        # TODO: permissions
        if self.settings_database_connector.get_room_owner_account_id(room_id) == account_id:
            success = self.settings_database_connector.edit_room_title(room_id, new_room_title)
            response = {"channel": "settings", "type": "edit_room_title", "success": success, "room_title": new_room_title}
            response_json = json.dumps(response, default=str)
            await websocket.send(response_json)


    async def edit_room_description(self, websocket, message):
        username = self.authentication_handler.usernames[websocket]
        account_id = self.settings_database_connector.get_id_for_username(username)
        new_room_description = message["room_description"]
        room_id = message["room_id"]
        # TODO: permissions
        if self.settings_database_connector.get_room_owner_account_id(room_id) == account_id:
            success = self.settings_database_connector.edit_room_description(room_id, new_room_description)
            response = {"channel": "settings", "type": "edit_room_description", "success": success, "room_description": new_room_description}
            response_json = json.dumps(response, default=str)
            await websocket.send(response_json)


    async def set_room_privacy(self, websocket, message):
        username = self.authentication_handler.usernames[websocket]
        account_id = self.settings_database_connector.get_id_for_username(username)
        success = self.settings_database_connector.set_room_privacy(account_id, message["room_id"], message["private"])
        response = {"channel": "settings", "type": "set_room_privacy", "success": success}
        response_json = json.dumps(response, default=str)
        await websocket.send(response_json)


    async def request_room_privacy(self, websocket, message):
        username = self.authentication_handler.usernames[websocket]
        account_id = self.settings_database_connector.get_id_for_username(username)
        private = self.settings_database_connector.get_room_privacy(message["room_id"])
        response = {"channel": "settings", "type": "request_room_privacy", "private": private}
        response_json = json.dumps(response, default=str)
        await websocket.send(response_json)


    async def create_invitation(self, websocket, message):
        # TODO: validate membership of this room!
        username = self.authentication_handler.usernames[websocket]
        inviter_account_id = self.settings_database_connector.get_id_for_username(username)
        invitee_account_id = self.settings_database_connector.get_id_for_username(message["invitee"])
        success = False
        if invitee_account_id is not None:
            success = self.settings_database_connector.create_invitation(inviter_account_id, message["room_id"], invitee_account_id)
        else:
            # invite them via email
            email = message["invitee"].lower()
            if EMAIL_REGEX.match(email) and not self.settings_database_connector.referral_exists(inviter_account_id, email):
                room_title = self.settings_database_connector.get_room_title(message["room_id"])
                self.emailer.send_referral_email(email, self.settings_database_connector.get_display_name_for_id(inviter_account_id), message["room_id"], room_title)
                # create a referral
                self.settings_database_connector.create_referral(inviter_account_id, email, message["room_id"])
                success = True
        response = {"channel": "settings", "type": "create_invitation", "success": success}
        response_json = json.dumps(response, default=str)
        await websocket.send(response_json)



    async def request_invitations(self, websocket, message):
        username = self.authentication_handler.usernames[websocket]
        account_id = self.settings_database_connector.get_id_for_username(username)
        invitations = self.settings_database_connector.get_incoming_invitations(account_id)
        invitations_a = []
        for invitation in invitations:
            invitation_a = {}
            invitation_a["invitation_id"] = invitation[0]
            invitation_a["username"] = self.settings_database_connector.get_username_for_id(invitation[1])
            invitation_a["room_id"] = invitation[2]
            invitation_a["room_title"] = self.settings_database_connector.get_room_title(invitation[2])
            invitations_a.append(invitation_a)
        response = {"channel": "settings", "type": "request_invitations", "invitations": invitations_a}
        response_json = json.dumps(response, default=str)
        await websocket.send(response_json)
    

    async def decline_invitation(self, websocket, message):
        # TODO: validate this is the correct owner of the invitation
        self.settings_database_connector.delete_invitation_by_id(message["invitation_id"])
        success = True # TODO
        response = {"channel": "settings", "type": "decline_invitation", "success": success}
        response_json = json.dumps(response, default=str)
        await websocket.send(response_json)
    

    async def request_room_members(self, websocket, message):
        username = self.authentication_handler.usernames[websocket]
        account_id = self.settings_database_connector.get_id_for_username(username)
        room_id = message["room_id"]
        if self.settings_database_connector.membership_exists(account_id, room_id):
            members = self.settings_database_connector.get_room_members(room_id)
            members_a = []
            for member in members:
                member_a = {}
                member_a["display_name"] = self.settings_database_connector.get_display_name_for_id(member[0])
                member_a["account_id"] = member[0]
                members_a.append(member_a)
                response = {"channel": "settings", "type": "request_room_members", "members": members_a}
                response_json = json.dumps(response, default=str)
            await websocket.send(response_json)