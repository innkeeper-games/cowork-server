# Handles JSON messages and starts the authentication server

import os

from pathlib import Path
from http.cookies import SimpleCookie

import asyncio
import logging

import ssl
import websockets, websockets.http
from http import HTTPStatus

from aiohttp import web
import aiohttp_cors

import json

import accounts

from scheduler import Scheduler

from authentication_handler import AuthenticationHandler

from room_handler import RoomHandler
from chat_handler import ChatHandler
from tasks_handler import TasksHandler
from settings_handler import SettingsHandler
from public_handler import PublicHandler
from timer_handler import TimerHandler
from stats_handler import StatsHandler

websocket_peers = set()

authenticated_peers = set()

scheduler = Scheduler()

auth_websocket = None
auth_api_key = os.environ.get("COWORK_AUTH_API_KEY")

queried_tokens = {}

authentication_handler = AuthenticationHandler(scheduler, auth_websocket)

room_handler = RoomHandler(authentication_handler, scheduler)
chat_handler = ChatHandler(authentication_handler, room_handler)
tasks_handler = TasksHandler(authentication_handler, room_handler)
settings_handler = SettingsHandler(authentication_handler, room_handler)
public_handler = PublicHandler(authentication_handler)
timer_handler = TimerHandler(authentication_handler, room_handler, scheduler)
stats_handler = StatsHandler(authentication_handler)

channels = {
    "auth": authentication_handler, "room": room_handler, "settings": settings_handler, "chat": chat_handler, "tasks": tasks_handler, \
        "public": public_handler, "timer": timer_handler, "stats": stats_handler
}

def add_websocket(websocket):
    global websocket_peers

    print("New peer connected to the main server.")
    websocket_peers.add(websocket)


async def remove_websocket(websocket):
    global websocket_peers

    print("A peer disconnected from the main server.")
    await channels["room"].remove_peer(websocket)
    websocket_peers.remove(websocket)


async def consumer(websocket, message):
    global channels

    if "channel" in message:
        if message["channel"] in channels:
            if "type" in message:
                if message["channel"] == "auth":
                    await channels[message["channel"]].consumer(websocket, message)
                elif message["channel"] == "public":
                    await channels[message["channel"]].consumer(websocket, message)
                elif websocket in authenticated_peers:
                    await channels[message["channel"]].consumer(websocket, message)
                else:
                    response = {"type": "sign_in", "username_exists": False, "password_correct": False}
                    response_json = json.dumps(response)
                    await websocket.send(response_json)
        else:
            print("There's no valid channel indicated; I cannot route the message.")
    return


async def connect_to_auth():
    global auth_websocket, auth_api_key

    async with websockets.connect("wss://ws.joincowork.com:4433/") as websocket:

        auth_websocket = websocket

        message = {"channel": "auth", "type": "register_server", "api_key": auth_api_key}
        message_json = json.dumps(message, default=str)
        await auth_websocket.send(message_json)

        while True:
            response_s = await auth_websocket.recv()
            print("< {}".format(response_s))

            response = json.loads(response_s)
            await auth_consumer(response)


async def auth_consumer(message):
    global auth_websocket
    
    print(message)

    if message["type"] == "get_session":
        if message["success"]:
            websocket = queried_tokens[message["token"]]
            if websocket in websocket_peers:
                queried_tokens.pop(message["token"])
                authenticated_peers.add(websocket)
                username = message["username"]
                channels["auth"].make_session(websocket, username)

                account_id = channels["auth"].auth_database_connector.get_id_for_username(username)
                display_name = channels["auth"].auth_database_connector.get_display_name_for_id(account_id)
                pro = channels["auth"].auth_database_connector.get_pro(account_id)
                update_notes = channels["auth"].auth_database_connector.get_update_notes(account_id)
                channels["auth"].auth_database_connector.update_last_login(account_id)
                response = {"type": "sign_in", "username": username, "account_id": account_id, "display_name": display_name, "username_exists": True, "password_correct": True, "update_notes": update_notes, "pro": pro}
                response_json = json.dumps(response)
                await websocket.send(response_json)
    elif message["type"] == "register_server":
        if message["success"]:
            channels["auth"].set_auth_websocket(auth_websocket)


async def request_session_is_valid(websocket, token):
    global auth_websocket

    message = {"channel": "auth", "type": "get_session", "token": token}
    message_json = json.dumps(message, default=str)
    await auth_websocket.send(message_json)

    queried_tokens[token] = websocket

async def consumer_handler(websocket, path):
    global channels

    add_websocket(websocket)
    
    if not websocket in authenticated_peers:
        if "cookie" in websocket.request_headers:
            cookies = websocket.request_headers["Cookie"]
            token = cookies[6:]
            
            await request_session_is_valid(websocket, token)
    try:
        async for message_json in websocket:
            message = json.loads(message_json)
            await consumer(websocket, message)
    except websockets.exceptions.ConnectionClosedError as err:
        print(err)
    finally:
        await remove_websocket(websocket)

ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
here = os.path.dirname(os.path.abspath(__file__))
cert_pem = os.path.join(here, "fullchain.pem")
key_pem = os.path.join(here, "privkey.pem")
ssl_context.load_cert_chain(cert_pem, keyfile=key_pem)

start_server = websockets.serve(consumer_handler, "ws.joincowork.com", 4434, ssl=ssl_context)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_until_complete(connect_to_auth())
asyncio.get_event_loop().run_forever()
