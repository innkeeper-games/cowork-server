from handler import Handler
from tasks_database_connector import TasksDatabaseConnector

from datetime import datetime

import json
from uuid import uuid4
import logging
import asyncio
from settings_database_connector import SettingsDatabaseConnector

# key is type, value is dictionary of requirements and types

message_templates = {
    "request_lists": {"type": "request_lists"},

    "request_tasks_for_list": {"type": "request_tasks_for_list", "list_id": str, "index": int},
    "request_player_information": { "type": "request_player_information", "persist_object_id": str},
    "request_task": {"type": "request_task", "task_id": str},
    "add_task": {"type": "add_task", "public": bool, "active": bool, "title": str, "contents": str, "list_id": str, "index": int},
    "edit_task_title": {"type": "edit_task_title", "task_id": str, "title": str},
    "edit_task_contents": {"type": "edit_task_contents", "task_id": str, "contents": str},
    "set_listing_active": {"type": "set_listing_active", "listing_id": str},
    "set_task_public": {"type": "set_task_public", "task_id": str, "public": bool},
    "set_task_archived": {"type": "set_task_public", "task_id": str, "archived": bool},
    "set_task_complete": {"type": "set_task_public", "task_id": str, "complete": bool},
    "delete_task": {"type": "delete_task", "task_id": str},

    "save_task": {"type": "save_task", "task_id": str},

    "add_list": {"type": "add_list", "title": str, "index": int},
    "delete_list": {"type": "delete_list", "list_id": str},
    "edit_list_title": {"type": "edit_list_title", "list_id": str, "title": str},    

    "edit_listing": {"type": "edit_listing", "listing_id": str, "index": int, "list_id": str},

    "move_list": {"type": "move_list", "index": int, "list_id": str},

    "add_assignment": {"type": "add_assignment", "task_id": str, "account_id": str},

    "request_tags": {"type": "request_tags"},
    "request_tasks_with_tags": {"type": "request_tasks_with_tags", "tags": list},
    "add_tag": {"type": "add_tag", "color": int, "title": str},
    "delete_tag": {"type": "delete_tag", "tag_id": str},
    "add_tagging": {"type": "add_tagging", "listing_id": str, "tag_id": str},
    "delete_tagging": {"type": "delete_tagging", "tagging_id": str}
    
}

class TasksHandler(Handler):

    def __init__(self, authentication_handler, room_handler):
        self.authentication_handler = authentication_handler
        self.room_handler = room_handler
        self.tasks_database_connector = TasksDatabaseConnector()
        self.on_active_listing_changed_functions = []


    def is_valid(self, message):
        global message_templates
            
        return Handler.is_valid(self, message_templates, message)


    async def consumer(self, websocket, message):
        message_valid = self.is_valid(message)
        session_valid = False
        if message_valid:
            if message["type"] == "request_lists":
                await self.request_lists(websocket, message)

            elif message["type"] == "request_tasks_for_list":
                await self.request_tasks_for_list(websocket, message)
            elif message["type"] == "request_player_information":
                await self.request_player_information(websocket, message)
            elif message["type"] == "request_task":
                await self.request_task(websocket, message)
            elif message["type"] == "add_task":
                await self.add_task(websocket, message)
            elif message["type"] == "edit_task_title":
                await self.edit_task_title(websocket, message)
            elif message["type"] == "edit_task_contents":
                await self.edit_task_contents(websocket, message)
            elif message["type"] == "set_listing_active":
                await self.set_listing_active(websocket, message)
            elif message["type"] == "set_task_public":
                await self.set_task_public(websocket, message)
            elif message["type"] == "set_listing_archived":
                await self.set_listing_archived(websocket, message)
            elif message["type"] == "set_task_complete":
                await self.set_task_complete(websocket, message)
            elif message["type"] == "delete_task":
                await self.delete_task(websocket, message)

            elif message["type"] == "save_task":
                await self.save_task(websocket, message)

            elif message["type"] == "edit_listing":
                await self.edit_listing(websocket, message)

            elif message["type"] == "move_list":
                await self.move_list(websocket, message)

            elif message["type"] == "add_assignment":
                await self.add_assignment(websocket, message)
    
            elif message["type"] == "request_tags":
                await self.request_tags(websocket, message)
            elif message["type"] == "request_tasks_with_tags":
                await self.request_tasks_with_tags(websocket, message)

            elif message["type"] == "add_tag":
                await self.add_tag(websocket, message)
            elif message["type"] == "delete_tag":
                await self.delete_tag(websocket, message)
            elif message["type"] == "add_tagging":
                await self.add_tagging(websocket, message)
            elif message["type"] == "delete_tagging":
                await self.delete_tagging(websocket, message)
        else:
            logging.error(
                "Message type is " + message["type"] + " " + str(message))
            logging.error(
                str(message_valid) + " " + str(session_valid))


    def add_list_for_account(self, account_id, title, index, room_id=None):
        return self.tasks_database_connector.add_list(account_id, title, index, room_id)


    async def request_lists(self, websocket, message):
        username = self.authentication_handler.usernames[websocket]
        account_id = self.tasks_database_connector.get_id_for_username(username)
        lists_a = []
        lists = self.tasks_database_connector.get_lists_for_account(account_id)
        if len(lists) == 0:
            self.add_list_for_account(account_id, "Tasks", 0)
            self.add_list_for_account(account_id, "Archive", 1, archive=True)
            lists = self.tasks_database_connector.get_lists_for_account(account_id)
        if len(lists) == 1:
            # TODO: temporarily necessary to migrate old accounts
            self.add_list_for_account(account_id, "Archive", 1, archive=True)
        for l in lists:
            l_a = {}
            l_a["list_id"] = l[0]
            l_a["title"] = l[1]
            l_a["index"] = l[2]
            l_a["archive"] = l[3]
            lists_a.append(l_a)
        response = {"channel": "tasks", "type": "request_lists", "lists": lists_a}
        response_json = json.dumps(response, default=str)
        await websocket.send(response_json)


    async def request_tasks_for_list(self, websocket, message):
        # for each task, the user must:
        # have a listing (even in INBOX or Public to <room name>)
        username = self.authentication_handler.usernames[websocket]
        account_id = self.tasks_database_connector.get_id_for_username(username)
        tasks_a = []
        listings = self.tasks_database_connector.get_listings_for_account_and_list(account_id, message["list_id"], message["index"], 10)
        tasks = self.tasks_database_connector.get_tasks_for_listings(listings)
        for i in range(len(tasks)):
            task_a = {}
            task_a["listing_id"] = listings[i][0]
            task_a["list_id"] = listings[i][2]
            task_a["index"] = listings[i][3]
            task_a["task_id"] = tasks[i][0]
            assignment_account_ids = self.tasks_database_connector.get_assignments_for_task(task_a["task_id"])
            assignment_usernames = []
            for assignment_account_id in assignment_account_ids:
                username = self.tasks_database_connector.get_username_for_id(assignment_account_id)
                assignment_usernames.append(username)
            task_a["assignments"] = assignment_usernames
            # should check if the listing id is valid for this person?
            task_a["tags"] = self.tasks_database_connector.get_tags_for_listing(task_a["listing_id"])
            task_a["public"] = tasks[i][1]
            task_a["complete"] = tasks[i][6]
            task_a["active"] = listings[i][4]
            task_a["title"] = tasks[i][3]
            task_a["contents"] = tasks[i][4]
            task_a["room_id"] = tasks[i][5]
            tasks_a.append(task_a)
        response = {"channel": "tasks", "type": "request_tasks_for_list", "list_id": message["list_id"], "tasks": tasks_a}
        response_json = json.dumps(response, default=str)
        await websocket.send(response_json)


    async def request_task(self, websocket, message):
        username = self.authentication_handler.usernames[websocket]
        account_id = self.tasks_database_connector.get_id_for_username(username)
        response = {"channel": "tasks", "type": "request_task"}
        task = self.tasks_database_connector.get_task(message["task_id"])
        account_has_task = self.tasks_database_connector.account_has_task(account_id, message["task_id"])
        if account_has_task or task[0]:
            assignment_account_ids = self.tasks_database_connector.get_assignments_for_task(message["task_id"])
            assignment_usernames = []
            for assignment_account_id in assignment_account_ids:
                username = self.tasks_database_connector.get_username_for_id(assignment_account_id)
                assignment_usernames.append(username)
            response["assignments"] = assignment_usernames
            response["task_id"] = task[0]
            response["public"] = task[1]
            response["active"] = task[2]
            response["title"] = task[3]
            response["contents"] = task[4]
            response["room_id"] = task[5]
            response["complete"] = task[6]
            response["has_listing"] = False
            if account_has_task:
                listing = self.tasks_database_connector.get_listing_for_account_and_task(account_id, message["task_id"])
                response["has_listing"] = True
                response["listing_id"] = listing[0]
                response["list_id"] = listing[1]
                response["index"] = listing[2]
                response["active"] = listing[3]
                response["tags"] = self.tasks_database_connector.get_tags_for_listing(response["listing_id"])
            response["can_edit_settings"] = False
            response["can_edit_contents"] = False
            response["can_edit_title"] = False
            account_can_edit_task = self.tasks_database_connector.account_can_edit_task(account_id, message["task_id"])
            if account_can_edit_task:
                response["can_edit_settings"] = True
                response["can_edit_contents"] = True
                response["can_edit_title"] = True
        response_json = json.dumps(response, default=str)
        await websocket.send(response_json)


    async def add_task(self, websocket, message):
        # create task,
        # create listing,
        # do NOT create assignment
        username = self.authentication_handler.usernames[websocket]
        account_id = self.tasks_database_connector.get_id_for_username(username)
        # verify that this account has this list
        # TODO: should we reply if they do not?
        if self.tasks_database_connector.account_has_list(account_id, message["list_id"]):
            # if index is valid
            size = len(self.tasks_database_connector.get_listings_for_account_and_list(account_id, message["list_id"]))
            if message["index"] >= 0 and message["index"] <= size:
                active = message["active"]
                if self.tasks_database_connector.get_active_listing_id(account_id) == None or size == 0:
                    active = True
                response = {"channel": "tasks", 
                    "type": "add_task",
                    "assignments": [],
                    "tags": [],
                    "public": message["public"],
                    "active": active,
                    "title": message["title"],
                    "contents": message["contents"],
                    "list_id": message["list_id"],
                    "index": message["index"]
                }
                # TODO: only allow one active task!!!
                if "room_id" in message:
                    response["room_id"] = message["room_id"]
                    response["task_id"] = self.tasks_database_connector.add_task(message["public"], active, message["title"], message["contents"], message["room_id"])
                else:
                    response["task_id"] = self.tasks_database_connector.add_task(message["public"], active, message["title"], message["contents"])
                response["listing_id"] = self.add_listing_for_account(account_id, response["task_id"], message["list_id"], message["index"])
                if active:
                    self.tasks_database_connector.set_listing_active(response["listing_id"], active)
                self.tasks_database_connector.add_task_permission(account_id, response["task_id"], True, True, True)
                response_json = json.dumps(response, default=str)
                await websocket.send(response_json)
        

    def add_listing_for_account(self, account_id, task_id, list_id, index):
        return self.tasks_database_connector.add_listing(account_id, task_id, list_id, index)


    async def edit_task_title(self, websocket, message):
        username = self.authentication_handler.usernames[websocket]
        account_id = self.tasks_database_connector.get_id_for_username(username)
        if self.tasks_database_connector.account_can_edit_task(account_id, message["task_id"]):
            self.tasks_database_connector.edit_task_title(message["task_id"], message["title"])
        response = {"channel": "tasks", "type": "edit_task_title", "task_id": message["task_id"], "title": message["title"]}
        response_json = json.dumps(response, default=str)
        await websocket.send(response_json)


    async def edit_task_contents(self, websocket, message):
        username = self.authentication_handler.usernames[websocket]
        account_id = self.tasks_database_connector.get_id_for_username(username)
        if self.tasks_database_connector.account_can_edit_task(account_id, message["task_id"]):
            self.tasks_database_connector.edit_task_contents(message["task_id"], message["contents"])
        response = {"channel": "tasks", "type": "edit_task_contents", "task_id": message["task_id"], "contents": message["contents"]}
        response_json = json.dumps(response, default=str)
        await websocket.send(response_json)
    

    def connect_to_active_listing_changed(self, func):
        self.connect_to_active_listing_changed.append(func)


    async def set_listing_active(self, websocket, message):
        username = self.authentication_handler.usernames[websocket]
        account_id = self.tasks_database_connector.get_id_for_username(username)
        if self.tasks_database_connector.account_has_listing(account_id, message["listing_id"]):

            if self.room_handler.peer_in_room(websocket):
                await self.room_handler.get_room_by_peer(websocket).on_peer_changed_active_listing_id(websocket, message["listing_id"])

            self.tasks_database_connector.set_listing_active(message["listing_id"], message["active"])
            for func in self.on_active_listing_changed_functions:
                func(message["listing_id"])
        response = {"channel": "tasks", "type": "set_listing_active", "listing_id": message["listing_id"], "active": message["active"]}
        response_json = json.dumps(response, default=str)
        await websocket.send(response_json)


    async def set_task_public(self, websocket, message):
        username = self.authentication_handler.usernames[websocket]
        account_id = self.tasks_database_connector.get_id_for_username(username)
        if self.tasks_database_connector.account_can_edit_task(account_id, message["task_id"]):
            self.tasks_database_connector.set_task_public(message["task_id"], message["public"])
        response = {"channel": "tasks", "type": "set_task_public", "task_id": message["task_id"], "public": message["public"]}
        response_json = json.dumps(response, default=str)
        await websocket.send(response_json)


    async def set_listing_archived(self, websocket, message):
        username = self.authentication_handler.usernames[websocket]
        account_id = self.tasks_database_connector.get_id_for_username(username)
        if self.tasks_database_connector.account_has_listing(account_id, message["listing_id"]):
            self.tasks_database_connector.set_listing_archived(message["listing_id"], message["archived"])
        response = {"channel": "tasks", "type": "set_task_archived", "listing_id": message["listing_id"], "archived": message["archived"]}
        response_json = json.dumps(response, default=str)
        await websocket.send(response_json)

        
    async def set_task_complete(self, websocket, message):
        username = self.authentication_handler.usernames[websocket]
        account_id = self.tasks_database_connector.get_id_for_username(username)
        if self.tasks_database_connector.account_can_edit_task(account_id, message["task_id"]):
            self.tasks_database_connector.set_task_complete(message["task_id"], message["complete"])
        response = {"channel": "tasks", "type": "set_task_complete", "task_id": message["task_id"], "complete": message["complete"]}
        response_json = json.dumps(response, default=str)
        await websocket.send(response_json)


    async def request_player_information(self, websocket, message):
        response = {
            "channel": "room", 
            "type": "request_player_information",
            "pro": self.authentication_handler.auth_database_connector.get_pro(message["persist_object_id"]),
            "public": False
        }
        listing_id = self.tasks_database_connector.get_active_listing_id(message["persist_object_id"])
        if listing_id is not None:
            task = self.tasks_database_connector.get_task_for_listing(listing_id)
            response["public"] = task[1]
            if response["public"]:
                response["task_id"] = task[0]
                response["active"] = task[2]
                response["complete"] = task[6]
                response["title"] = task[3]
                response["contents"] = task[4]
                response["room_id"] = task[5]
        response["persist_object_id"] = message["persist_object_id"]
        response_json = json.dumps(response, default=str)
        await websocket.send(response_json)


    async def delete_task(self, websocket, message):
        # delete the listing of this task for this user
        # delete this account's assignment to that task if it exists
        # if a task has no more listings, delete it as well (handled in database connector)
        username = self.authentication_handler.usernames[websocket]
        account_id = self.tasks_database_connector.get_id_for_username(username)
        listing = self.tasks_database_connector.delete_listing_for_task_and_account(message["task_id"], account_id)
        self.tasks_database_connector.delete_assignment(account_id, message["task_id"])
        response = {"channel": "tasks", "type": "delete_task", "task_id": message["task_id"]}
        response_json = json.dumps(response, default=str)
        await websocket.send(response_json)


    async def save_task(self, websocket, message):
        username = self.authentication_handler.usernames[websocket]
        account_id = self.tasks_database_connector.get_id_for_username(username)
        task = self.tasks_database_connector.get_task(message["task_id"])        
        task_id = task[0]
        public = task[1]
        # if public or shared with user (only public available for now)
        if public and not self.tasks_database_connector.account_has_task(account_id, task_id):
            # add to the first available list now; we will eventually abandon lists
            # in favor of tags
            list_to_add_to_id = self.tasks_database_connector.get_lists_for_account(account_id)[0][0]
            listing = self.add_listing_for_account(account_id, task_id, list_to_add_to_id, 0)

            listing_response = {"channel": "tasks", "type": "save_task", "task_id": task_id}
            task_response = {"channel": "tasks", 
                        "type": "add_task",
                        "assignments": [],
                        "public": public,
                        "active": task[2],
                        "title": task[3],
                        "contents": task[4],
                        "listing_id": listing[0],
                        "list_id": list_to_add_to_id,
                        "task_id": task_id,
                        "index": 0
                    }
            listing_response_json = json.dumps(listing_response, default=str)
            task_response_json = json.dumps(task_response, default=str)
            await websocket.send(task_response_json)
            await websocket.send(listing_response_json)


    async def edit_listing(self, websocket, message):
        username = self.authentication_handler.usernames[websocket]
        account_id = self.tasks_database_connector.get_id_for_username(username)
        if self.tasks_database_connector.account_has_list(account_id, message["list_id"]) and self.tasks_database_connector.account_has_listing(account_id, message["listing_id"]):
            # if index is valid
            if message["index"] >= 0 and message["index"] <= len(self.tasks_database_connector.get_listings_for_account_and_list(account_id, message["list_id"])):
                self.tasks_database_connector.edit_listing(message["listing_id"], message["list_id"], message["index"])


    async def add_assignment(self, websocket, message):
        # validate that the task exists and that this account (i.e. sender) can access it
        # create assignment
        # create listing if the assigned account doesn't have one already
        # (if no "inbox" list, create "inbox" list)
        username = self.authentication_handler.usernames[websocket]
        account_id = self.tasks_database_connector.get_id_for_username(username)
        if self.tasks_database_connector.account_can_edit_task(account_id, message["task_id"]):
            self.tasks_database_connector.add_assignment(account_id, message["task_id"])
            assigned_account_id = self.tasks_database_connector.get_id_for_username(message["account_id"])
            if assigned_account_id is not None:
                if not self.tasks_database_connector.account_has_task(assigned_account_id, message["task_id"]):
                    # check if the assigned user has an inbox list
                    list_id = self.tasks_database_connector.account_has_inbox_list(assigned_account_id)
                    if list_id is None:
                        list_id = self.add_list_for_account(assigned_account_id, "Inbox", 0, True)
                    self.tasks_database_connector.add_listing(account_id, message["task_id"], list_id, 0)
        response = {"channel": "tasks", "type": "add_assignment", "display_name": self.tasks_database_connector.get_display_name_for_id(assigned_account_id), "task_id": message["task_id"]}
        response_json = json.dumps(response, default=str)
        await websocket.send(response_json)


    async def request_tags(self, websocket, message):
        username = self.authentication_handler.usernames[websocket]
        account_id = self.tasks_database_connector.get_id_for_username(username)
        tags_a = []
        tags = self.tasks_database_connector.get_tags_for_account(account_id)
        for t in tags:
            t_a = {}
            t_a["tag_id"] = t[0]
            t_a["color"] = t[1]
            t_a["title"] = t[2]
            tags_a.append(t_a)
        response = {"channel": "tasks", "type": "request_tags", "tags": tags_a}
        response_json = json.dumps(response, default=str)
        await websocket.send(response_json)
    

    async def request_tasks_with_tags(self, websocket, message):
        # should this actually be the client's job? what about when they have tons of tasks?
        pass


    async def add_tag(self, websocket, message):
        username = self.authentication_handler.usernames[websocket]
        account_id = self.tasks_database_connector.get_id_for_username(username)
        response = {"channel": "tasks", "type": "add_tag", "color": message["color"], "title": message["title"]}
        response["tag_id"] = self.tasks_database_connector.add_tag(account_id, message["color"], message["title"])
        response_json = json.dumps(response, default=str)
        await websocket.send(response_json)


    async def delete_tag(self, websocket, message):
        username = self.authentication_handler.usernames[websocket]
        account_id = self.tasks_database_connector.get_id_for_username(username)
        if self.tasks_database_connector.account_can_use_tag(account_id, message["tag_id"]):
            self.tasks_database_connector.delete_tag(message["tag_id"])
            response = {"channel": "tasks", "type": "delete_tag", "tag_id": message["tag_id"]}
            response_json = json.dumps(response, default=str)
            await websocket.send(response_json)


    async def add_tagging(self, websocket, message):
        # create tagging
        username = self.authentication_handler.usernames[websocket]
        account_id = self.tasks_database_connector.get_id_for_username(username)
        if self.tasks_database_connector.account_has_listing(account_id, message["listing_id"]):
            if self.tasks_database_connector.account_can_use_tag(account_id, message["tag_id"]):
                tag = self.tasks_database_connector.get_tag(message["tag_id"])
                existing_taggings = self.tasks_database_connector.get_tags_for_listing(message["listing_id"])
                for tagging in existing_taggings:
                    if tagging["tag_id"] == message["tag_id"]:
                        return
                tagging_id = self.tasks_database_connector.add_tagging(message["tag_id"], message["listing_id"])
                response = {"channel": "tasks", "type": "add_tagging", "tag_id": tag[0], "color": tag[2], "title": tag[1], "tagging_id": tagging_id, "listing_id": message["listing_id"]}
                response_json = json.dumps(response, default=str)
                await websocket.send(response_json)


    async def delete_tagging(self, websocket, message):
        username = self.authentication_handler.usernames[websocket]
        account_id = self.tasks_database_connector.get_id_for_username(username)
        print("trying to delete a tagging")
        if self.tasks_database_connector.account_has_tagging(account_id, message["tagging_id"]):
            print("account has tagging")
            self.tasks_database_connector.delete_tagging(message["tagging_id"])
            response = {"channel": "tasks", "type": "delete_tagging", "tagging_id": message["tagging_id"]}
            response_json = json.dumps(response, default=str)
            await websocket.send(response_json)


    def add_list_for_account(self, account_id, title, index, inbox=False, room_id=None, archive=False):
        return self.tasks_database_connector.add_list(account_id, title, index, inbox, room_id, archive)